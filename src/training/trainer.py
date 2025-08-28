import os
import json
import torch
import torch.nn.functional as F
from tqdm import tqdm
from accelerate import Accelerator
from .scheduler import create_scheduler
from .metrics import setup_metrics
from .loss_function import MultiClassFocalLossWithAlpha
import wandb
from models.model_factory import create_plm_and_tokenizer
from peft import PeftModel

class Trainer:
    def __init__(self, args, model, plm_model, logger, train_loader):
        self.args = args
        self.model = model
        self.plm_model = plm_model
        self.logger = logger
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.train_loader = train_loader
        
        # Log column name override information if available
        self._log_column_override_info()
        
        # Setup metrics
        self.metrics_dict = setup_metrics(args)
        
        # Setup optimizer with different learning rates
        if self.args.training_method == 'full':
            # Use a smaller learning rate for PLM
            optimizer_grouped_parameters = [
                {
                    "params": self.model.parameters(),
                    "lr": args.learning_rate
                },
                {
                    "params": self.plm_model.parameters(),
                    "lr": args.learning_rate
                }
            ]
            self.optimizer = torch.optim.AdamW(optimizer_grouped_parameters)
        elif self.args.training_method in ['plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3']:
            optimizer_grouped_parameters = [
                {
                    "params": self.model.parameters(),
                    "lr": args.learning_rate                    
                },
                {
                    "params": [param for param in self.plm_model.parameters() if param.requires_grad],
                    "lr": args.learning_rate
                }
            ]
            self.optimizer = torch.optim.AdamW(optimizer_grouped_parameters)
        else:
            self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=args.learning_rate)
        
        # Setup accelerator
        self.accelerator = Accelerator(gradient_accumulation_steps=args.gradient_accumulation_steps)
        
        # Setup scheduler
        self.scheduler = create_scheduler(args, self.optimizer, self.train_loader)
        
        # Setup loss function
        self.loss_fn = self._setup_loss_function()
        
        # Prepare for distributed training
        if self.args.training_method in ['full', 'plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3']:
            self.model, self.plm_model, self.optimizer = self.accelerator.prepare(
                self.model, self.plm_model, self.optimizer
            )
        else:
            self.model, self.optimizer = self.accelerator.prepare(self.model, self.optimizer)
        if self.scheduler:
            self.scheduler = self.accelerator.prepare(self.scheduler)
            
        # Training state
        self.best_val_loss = float("inf")
        if self.args.monitor_strategy == 'min':
            self.best_val_metric_score = float("inf")
        else:
            self.best_val_metric_score = -float("inf")
        self.global_steps = 0
        self.early_stop_counter = 0
        
        # Save args
        with open(os.path.join(self.args.output_dir, f'{self.args.output_model_name.split(".")[0]}.json'), 'w') as f:
            json.dump(self.args.__dict__, f)
    
    def _log_column_override_info(self):
        """Log column name override information if available."""
        if hasattr(self.args, '_column_override_info'):
            for key, info in self.args._column_override_info.items():
                if 'old' in info and 'new' in info:
                    self.logger.info(f"Overriding {key}: {info['old']} -> {info['new']}")
                elif 'default' in info:
                    self.logger.info(f"Using default {key}: {info['default']}")
        else:
            # Fallback to current values if no override info is available
            self.logger.info(f"Using sequence column: {self.args.sequence_column_name}")
            self.logger.info(f"Using label column: {self.args.label_column_name}")
        
    def _setup_loss_function(self):
        if self.args.problem_type == 'regression':
            return torch.nn.MSELoss()
        elif self.args.problem_type == 'multi_label_classification':
            return torch.nn.BCEWithLogitsLoss()
        elif "residue" in self.args.problem_type:
            # For residue-level classification, we need to handle sequence-level loss
            return torch.nn.CrossEntropyLoss(ignore_index=-1)  # Ignore padding tokens (-1)
        else:
            return torch.nn.CrossEntropyLoss()
    
    def train(self, train_loader, val_loader):
        """Train the model."""
        for epoch in range(self.args.num_epochs):
            self.logger.info(f"---------- Epoch {epoch} ----------")
            
            # Training phase
            train_loss = self._train_epoch(train_loader)
            self.logger.info(f'Epoch {epoch} Train Loss: {train_loss:.4f}')
            
            # Validation phase
            val_loss, val_metrics = self._validate(val_loader)
            
            # Handle validation results (model saving, early stopping)
            self._handle_validation_results(epoch, val_loss, val_metrics)
            
            # Early stopping check
            if self._check_early_stopping():
                self.logger.info(f"Early stop at Epoch {epoch}")
                break
                
    def _train_epoch(self, train_loader):
        self.model.train()
        if self.args.training_method in  ['full', 'plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3']:
            self.plm_model.train()
        total_loss = 0
        total_samples = 0
        epoch_iterator = tqdm(train_loader, desc="Training")
        
        for batch in epoch_iterator:
            # choose models to accumulate
            models_to_accumulate = [self.model, self.plm_model] if self.args.training_method in  ['full', 'plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3'] else [self.model]
            
            with self.accelerator.accumulate(*models_to_accumulate):
                # Forward and backward
                loss = self._training_step(batch)
                self.accelerator.backward(loss)
                    
                # Update statistics
                batch_size = batch[self.args.label_column_name].size(0)
                total_loss += loss.item() * batch_size
                total_samples += batch_size
                
                # Gradient clipping if needed
                if self.args.max_grad_norm > 0:
                    params_to_clip = (
                        list(self.model.parameters()) + list(self.plm_model.parameters())
                        if self.args.training_method in  ['full', 'plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3']
                        else self.model.parameters()
                    )
                    self.accelerator.clip_grad_norm_(params_to_clip, self.args.max_grad_norm)
                
                # Optimization step
                self.optimizer.step()
                if self.scheduler:
                    self.scheduler.step()
                self.optimizer.zero_grad()
                
                # Logging
                self.global_steps += 1
                self._log_training_step(loss)
                
                # Update progress bar
                epoch_iterator.set_postfix(
                    train_loss=loss.item(),
                    grad_step=self.global_steps // self.args.gradient_accumulation_steps
                )
        
        return total_loss / total_samples
    
    def _training_step(self, batch):
        # Move batch to device
        batch = {k: v.to(self.device) for k, v in batch.items()}
        
        # Store current batch for metrics update
        self.current_batch = batch
        
        # Forward pass
        logits = self.model(self.plm_model, batch)
        loss = self._compute_loss(logits, batch[self.args.label_column_name])
        
        return loss
    
    def _validate(self, val_loader):
        """
        Validate the model.
        
        Args:
            val_loader: Validation data loader
        
        Returns:
            tuple: (validation_loss, validation_metrics)
        """
        self.model.eval()
        if self.args.training_method in  ['full', 'plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3']:
            self.plm_model.eval()
            
        total_loss = 0
        total_samples = 0
        
        # Reset all metrics at the start of validation
        for metric in self.metrics_dict.values():
            metric.reset()
        
        with torch.no_grad():
            for batch in tqdm(val_loader, desc="Validating"):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                
                # Store current batch for metrics update
                self.current_batch = batch
                
                # Forward pass
                logits = self.model(self.plm_model, batch)
                loss = self._compute_loss(logits, batch[self.args.label_column_name])
                
                # Update loss statistics
                batch_size = len(batch[self.args.label_column_name])
                total_loss += loss.item() * batch_size
                total_samples += batch_size
                
                # Update metrics
                self._update_metrics(logits, batch[self.args.label_column_name])
        
        # Compute average loss
        avg_loss = total_loss / total_samples
        
        # Compute final metrics
        metrics_results = {name: metric.compute().item() 
                          for name, metric in self.metrics_dict.items()}
        
        return avg_loss, metrics_results
    
    def test(self, test_loader):
        # Load best model
        self._load_best_model()
        
        # Add a clear signal that testing is starting
        self.logger.info("---------- Starting Test Phase ----------")
        
        # Run evaluation with a custom testing function instead of reusing _validate
        test_loss, test_metrics = self._test_evaluate(test_loader)
        
        # Log results
        self.logger.info("Test Results:")
        self.logger.info(f"Test Loss: {test_loss:.4f}")
        for name, value in test_metrics.items():
            self.logger.info(f"Test {name}: {value:.4f}")
            
        if self.args.wandb:
            wandb.log({f"test/{k}": v for k, v in test_metrics.items()})
            wandb.log({"test/loss": test_loss})
    
    def _test_evaluate(self, test_loader):
        """
        Dedicated evaluation function for test phase with proper labeling.
        This is almost identical to _validate but with "Testing" progress bar.
        """
        self.model.eval()
        if self.args.training_method in ['full', 'plm-lora', 'plm-qlora', 'plm-dora', 'plm-adalora', 'plm-ia3']:
            self.plm_model.eval()
            
        total_loss = 0
        total_samples = 0
        
        # Reset all metrics at the start of testing
        for metric in self.metrics_dict.values():
            metric.reset()
        
        with torch.no_grad():
            # Note the desc is "Testing" instead of "Validating"
            for batch in tqdm(test_loader, desc="Testing"):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                
                # Store current batch for metrics update
                self.current_batch = batch
                
                # Forward pass
                logits = self.model(self.plm_model, batch)
                loss = self._compute_loss(logits, batch[self.args.label_column_name])
                
                # Update loss statistics
                batch_size = len(batch[self.args.label_column_name])
                total_loss += loss.item() * batch_size
                total_samples += batch_size
                
                # Update metrics
                self._update_metrics(logits, batch[self.args.label_column_name])
        
        # Compute average loss
        avg_loss = total_loss / total_samples
        
        # Compute final metrics
        metrics_results = {name: metric.compute().item() 
                          for name, metric in self.metrics_dict.items()}
        
        return avg_loss, metrics_results
    
    def _compute_loss(self, logits, labels):
        if self.args.problem_type == 'regression' and self.args.num_labels == 1:
            return self.loss_fn(logits.squeeze(), labels.squeeze())
        elif self.args.problem_type == 'multi_label_classification':
            return self.loss_fn(logits, labels.float())
        elif "residue" in self.args.problem_type:
            # For residue-level classification, reshape logits and labels
            # logits: [batch_size, seq_len, num_classes] -> [batch_size * seq_len, num_classes]
            # labels: [batch_size, seq_len] -> [batch_size * seq_len]
            batch_size, seq_len, num_classes = logits.shape
            
            # Ensure labels have the correct shape
            if labels.dim() == 1:
                # If labels is [batch_size], expand to [batch_size, seq_len]
                labels = labels.unsqueeze(1).expand(-1, seq_len)
            
            logits_flat = logits.view(-1, num_classes)
            labels_flat = labels.view(-1)
            
            # Ensure shapes match
            assert logits_flat.size(0) == labels_flat.size(0), f"Logits and labels batch size mismatch: {logits_flat.size(0)} vs {labels_flat.size(0)}"
            
            return self.loss_fn(logits_flat, labels_flat)
        else:
            return self.loss_fn(logits, labels)
    
    def _update_metrics(self, logits, labels):
        """Update metrics with current batch predictions."""
        for metric_name, metric in self.metrics_dict.items():
            if self.args.problem_type == 'regression' and self.args.num_labels == 1:
                logits = logits.view(-1, 1)
                labels = labels.view(-1, 1)
                metric(logits, labels)
            elif self.args.problem_type == 'multi_label_classification':
                metric(torch.sigmoid(logits), labels)
            elif "residue" in self.args.problem_type:
                # For residue-level classification, pass attention mask if available
                attention_mask = None
                if "aa_seq_attention_mask" in self.current_batch:
                    attention_mask = self.current_batch["aa_seq_attention_mask"]
                
                # Update residue-specific metrics
                metric.update(logits, labels, attention_mask)
            else:
                if self.args.num_labels == 2:
                    if metric_name == 'auroc':
                        metric(torch.sigmoid(logits[:, 1]), labels)
                    else:
                        metric(torch.argmax(logits, 1), labels)
                else:
                    if metric_name == 'auroc':
                        metric(F.softmax(logits, dim=1), labels)
                    else:
                        metric(torch.argmax(logits, 1), labels)
    
    def _log_training_step(self, loss):
        if self.args.wandb:
            wandb.log({
                "train/loss": loss.item(),
                "train/learning_rate": self.optimizer.param_groups[0]['lr']
            }, step=self.global_steps)
    
  
    def _save_model(self, path):
        if self.args.training_method in ['full', 'lora']:
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            plm_state = {k: v.cpu() for k, v in self.plm_model.state_dict().items()}
            torch.save({
                'model_state_dict': model_state,
                'plm_state_dict': plm_state
            }, path)
        elif self.args.training_method == "plm-lora":
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            torch.save(model_state, path)
            plm_lora_path = path.replace('.pt', '_lora')
            self.plm_model.save_pretrained(plm_lora_path)
        elif self.args.training_method == "plm-qlora":
            # save model state dict
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            torch.save(model_state, path)
            plm_qlora_path = path.replace('.pt', '_qlora')
            # save plm model lora weights
            self.plm_model.save_pretrained(plm_qlora_path)
        elif self.args.training_method == "plm-dora":
            # save model state dict
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            torch.save(model_state, path)
            plm_dora_path = path.replace('.pt', '_dora')
            # save plm model lora weights
            self.plm_model.save_pretrained(plm_dora_path)
        elif self.args.training_method == "plm-adalora":
            # save model state dict
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            torch.save(model_state, path)
            plm_adalora_path = path.replace('.pt', '_adalora')
            self.plm_model.save_pretrained(plm_adalora_path)
        elif self.args.training_method == "plm-ia3":
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            torch.save(model_state, path)
            plm_ia3_path = path.replace('.pt', '_ia3')
            self.plm_model.save_pretrained(plm_ia3_path)
        else:
            model_state = {k: v.cpu() for k, v in self.model.state_dict().items()}
            torch.save(model_state, path)

    def _load_best_model(self):
        path = os.path.join(self.args.output_dir, self.args.output_model_name)
        if self.args.training_method in ['full', 'lora']:
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.plm_model.load_state_dict(checkpoint['plm_state_dict'])
            self.model.to(self.device)
            self.plm_model.to(self.device)
        elif self.args.training_method == "plm-lora":
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint)
            plm_lora_path = path.replace('.pt', '_lora')
            _, self.plm_model = create_plm_and_tokenizer(self.args)
            self.plm_model = PeftModel.from_pretrained(self.plm_model, plm_lora_path)
            self.plm_model = self.plm_model.merge_and_unload()
            self.model.to(self.device)
            self.plm_model.to(self.device)
        elif self.args.training_method == "plm-qlora":
            # load model state dict
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint)
            plm_qlora_path = path.replace('.pt', '_qlora')
            # reload plm model and apply qlora weights
            _, self.plm_model = create_plm_and_tokenizer(self.args)
            self.plm_model = PeftModel.from_pretrained(self.plm_model, plm_qlora_path)
            self.plm_model = self.plm_model.merge_and_unload()
            self.model.to(self.device)
            self.plm_model.to(self.device)
        elif self.args.training_method == "plm-dora":
            # load model state dict
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint)
            plm_dora_path = path.replace('.pt', '_dora')
            # reload plm model and apply dora weights
            _, self.plm_model = create_plm_and_tokenizer(self.args)
            self.plm_model = PeftModel.from_pretrained(self.plm_model, plm_dora_path)
            self.plm_model = self.plm_model.merge_and_unload()
            self.model.to(self.device)
            self.plm_model.to(self.device)
        elif self.args.training_method == "plm-adalora":
            # load model state dict
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint)
            plm_adalora_path = path.replace('.pt', '_adalora')
            # reload plm model and apply adalora weights
            _, self.plm_model = create_plm_and_tokenizer(self.args)
            self.plm_model = PeftModel.from_pretrained(self.plm_model, plm_adalora_path)
            self.plm_model = self.plm_model.merge_and_unload()
            self.model.to(self.device)
            self.plm_model.to(self.device)
        elif self.args.training_method == "plm-ia3":
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint)
            plm_ia3_path = path.replace('.pt', '_ia3')
            _, self.plm_model = create_plm_and_tokenizer(self.args)
            self.plm_model = PeftModel.from_pretrained(self.plm_model, plm_ia3_path)
            self.plm_model = self.plm_model.merge_and_unload()
            self.model.to(self.device)
            self.plm_model.to(self.device)
        else:
            checkpoint = torch.load(path, map_location="cpu")
            self.model.load_state_dict(checkpoint)
            self.model.to(self.device)
    
    def _handle_validation_results(self, epoch: int, val_loss: float, val_metrics: dict):
        """
        Handle validation results, including model saving and early stopping checks.
        
        Args:
            epoch: Current epoch number
            val_loss: Validation loss
            val_metrics: Dictionary of validation metrics
        """
        # Log validation results
        self.logger.info(f'Epoch {epoch} Val Loss: {val_loss:.4f}')
        for metric_name, metric_value in val_metrics.items():
            self.logger.info(f'Epoch {epoch} Val {metric_name}: {metric_value:.4f}')
        
        if self.args.wandb:
            wandb.log({
                "val/loss": val_loss,
                **{f"val/{k}": v for k, v in val_metrics.items()}
            }, step=self.global_steps)
        
        # Check if we should save the model
        should_save = False
        monitor_value = val_loss
        
        # If monitoring a specific metric
        if self.args.monitor != 'loss' and self.args.monitor in val_metrics:
            monitor_value = val_metrics[self.args.monitor]
        
        # Check if current result is better
        if self.args.monitor_strategy == 'min':
            if monitor_value < self.best_val_metric_score:
                should_save = True
                self.best_val_metric_score = monitor_value
                self.early_stop_counter = 0
            else:
                self.early_stop_counter += 1
        else:  # strategy == 'max'
            if monitor_value > self.best_val_metric_score:
                should_save = True
                self.best_val_metric_score = monitor_value
                self.early_stop_counter = 0
            else:
                self.early_stop_counter += 1
        
        # Save model if improved
        if should_save:
            self.logger.info(f"Saving model with best val {self.args.monitor}: {monitor_value:.4f}")
            save_path = os.path.join(self.args.output_dir, self.args.output_model_name)
            self._save_model(save_path)

    def _check_early_stopping(self) -> bool:
        """
        Check if training should be stopped early.
        
        Returns:
            bool: True if training should stop, False otherwise
        """
        if self.args.patience > 0 and self.early_stop_counter >= self.args.patience:
            self.logger.info(f"Early stopping triggered after {self.early_stop_counter} epochs without improvement")
            return True
        return False 
