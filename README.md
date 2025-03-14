![# VenusFactory](img/banner.png)

Recent News:

- Welcome to VenusFactory!

## ✏️ Table of Contents

- [Features](#-features)
- [Supported Models](#-supported-models)
- [Supported Training Approaches](#-supported-training-approaches)
- [Supported Datasets](#-supported-datasets)
- [Supported Metrics](#-supported-metrics)
- [Reuirement](#-reuirement)
- [Get Started](#-get-started)
- [Citation](#-citation)
- [Acknowledgement](#-acknowledgement)

## 📑 Features

- **Vaious protein langugae models**: ESM2, ESM-b, ESM-1v, ProtBert, ProtT5, Ankh, etc
- **Comprehensive supervised datasets**: Localization, Fitness, Solubility, Stability, etc
- **Easy and quick data collector**: AlphaFold2 Database, RCSB, InterPro, Uniprot, etc
- **Experiment moitors**: Wandb, Local
- **Friendly interface**: Gradio UI

## 🤖 Supported Models

| Model                                                        | Model size              | Template                        |
| ------------------------------------------------------------ | ----------------------- | ------------------------------- |
| [ESM2](https://huggingface.co/facebook/esm2_t33_650M_UR50D)  | 8M/35M/150M/650M/3B/15B | facebook/esm2_t33_650M_UR50D    |
| [ESM-1b](https://huggingface.co/facebook/esm1b_t33_650M_UR50S) | 650M                    | facebook/esm1b_t33_650M_UR50S   |
| [ESM-1v](https://huggingface.co/facebook/esm1v_t33_650M_UR90S_1) | 650M                    | facebook/esm1v_t33_650M_UR90S_1 |
| [ProtBert-Uniref100](https://huggingface.co/Rostlab/prot_bert) | 420M                    | Rostlab/prot_bert_uniref100          |
| [ProtBert-BFD100](https://huggingface.co/Rostlab/prot_bert_bfd) | 420M                    | Rostlab/prot_bert_bfd           |
| [IgBert](https://huggingface.co/Exscientia/IgBert) | 420M                    | Exscientia/IgBert           |
| [IgBert_unpaired](https://huggingface.co/Exscientia/IgBert_unpaired) | 420M                    | Exscientia/IgBert_unpaired           |
| [ProtT5-Uniref50](https://huggingface.co/Rostlab/prot_t5_xl_uniref50) | 3B/11B                  | Rostlab/prot_t5_xl_uniref50     |
| [ProtT5-BFD100](https://huggingface.co/Rostlab/prot_t5_xl_bfd) | 3B/11B                  | Rostlab/prot_t5_xl_bfd          |
| [IgT5](https://huggingface.co/Exscientia/IgT5) | 3B                  | Exscientia/IgT5          |
| [IgT5_unpaired](https://huggingface.co/Exscientia/IgT5_unpaired) | 3B                  | Exscientia/IgT5_unpaired          |
| [Ankh](https://huggingface.co/ElnaggarLab/ankh-base)         | 450M/1.2B               | ElnaggarLab/ankh-base           |
| [ProSST](https://huggingface.co/AI4Protein/ProSST-2048)  |110M                     |AI4Protein/ProSST-2048     |
| [ProPrime](https://huggingface.co/AI4Protein/Prime_690M)  |690M                     |AI4Protein/Prime_690M     |

## 🔬 Supported Training Approaches

| Approach               | Full-tuning | Freeze-tuning      | SES-Adapter        | LoRA               |
| ---------------------- | ----------- | ------------------ | ------------------ | ------------------ |
| Pre-Training           | ❎          | ❎                | ❎                 | ❎                |
| Supervised Fine-Tuning | ✅          | ✅                | ✅                 | ✅                |

| Approach               | QLoRA       | DoRA               | AdaLoRA            | IA3                | 
| ---------------------- | ----------- | ------------------ | ------------------ | ------------------ |
| Pre-Training           | ❎          | ❎                | ❎                 | ❎                | 
| Supervised Fine-Tuning | ✅          | ✅                | ✅                 | ✅                |
## 📚 Supported Datasets

<details><summary>Pre-training datasets</summary>


- [CATH_V43_S40](https://huggingface.co/datasets/tyang816/cath) | structures

</details>

<details><summary>Supervised fine-tuning datasets (amino acid sequences/ foldseek sequences/ ss8 sequences)</summary>

- [DeepLocBinary_AlphaFold2](https://huggingface.co/datasets/tyang816/DeepLocBinary_AlphaFold2) | protein-wise | single_label_classification
- [DeepLocBinary_ESMFold](https://huggingface.co/datasets/tyang816/DeepLocBinary_ESMFold) | protein-wise | single_label_classification
- [DeepLocMulti_AlphaFold2](https://huggingface.co/datasets/tyang816/DeepLocMulti_AlphaFold2) | protein-wise | single_label_classification
- [DeepLocMulti_ESMFold](https://huggingface.co/datasets/tyang816/DeepLocMulti_ESMFold) | protein-wise | single_label_classification
- [DeepSol_ESMFold](https://huggingface.co/datasets/tyang816/DeepSol_ESMFold) | protein-wise | single_label_classification
- [DeepSoluE_ESMFold](https://huggingface.co/datasets/tyang816/DeepSoluE_ESMFold) | protein-wise | single_label_classification
- [ProtSolM_ESMFold](https://huggingface.co/datasets/tyang816/ProtSolM_ESMFold) | protein-wise | single_label_classification
- [eSOL_AlphaFold2](https://huggingface.co/datasets/tyang816/eSOL_AlphaFold2) | protein-wise | regression
- [eSOL_ESMFold](https://huggingface.co/datasets/tyang816/eSOL_ESMFold) | protein-wise | regression
- [DeepET_Topt_AlphaFold2](https://huggingface.co/datasets/tyang816/DeepET_Topt_AlphaFold2) | protein-wise | regression
- [DeepET_Topt_ESMFold](https://huggingface.co/datasets/tyang816/DeepET_Topt_ESMFold) | protein-wise | regression
- [EC_AlphaFold2](https://huggingface.co/datasets/tyang816/EC_AlphaFold2) | protein-wise | multi_label_classification
- [EC_ESMFold](https://huggingface.co/datasets/tyang816/EC_ESMFold) | protein-wise | multi_label_classification
- [GO_BP_AlphaFold2](https://huggingface.co/datasets/tyang816/GO_BP_AlphaFold2) | protein-wise | multi_label_classification
- [GO_BP_ESMFold](https://huggingface.co/datasets/tyang816/GO_BP_ESMFold) | protein-wise | multi_label_classification
- [GO_CC_AlphaFold2](https://huggingface.co/datasets/tyang816/GO_CC_AlphaFold2) | protein-wise | multi_label_classification
- [GO_CC_ESMFold](https://huggingface.co/datasets/tyang816/GO_CC_ESMFold) | protein-wise | multi_label_classification
- [GO_MF_AlphaFold2](https://huggingface.co/datasets/tyang816/GO_MF_AlphaFold2) | protein-wise | multi_label_classification
- [GO_MF_ESMFold](https://huggingface.co/datasets/tyang816/GO_MF_ESMFold) | protein-wise | multi_label_classification
- [MetalIonBinding_AlphaFold2](https://huggingface.co/datasets/tyang816/MetalIonBinding_AlphaFold2) | protein-wise | single_label_classification
- [MetalIonBinding_ESMFold](https://huggingface.co/datasets/tyang816/MetalIonBinding_ESMFold) | protein-wise | single_label_classification
- [Thermostability_AlphaFold2](https://huggingface.co/datasets/tyang816/Thermostability_ESMFold) | protein-wise | regression
- [Thermostability_ESMFold](https://huggingface.co/datasets/tyang816/Thermostability_ESMFold) | protein-wise | regression

> ✨ Only structural sequences are different for the same dataset, for example, ``DeepLocBinary_ESMFold`` and ``DeepLocBinary_AlphaFold2`` share the same amino acid sequences, this means if you only want to use the ``aa_seqs``, both are ok! 

</details>

<details><summary>Supervised fine-tuning datasets (amino acid sequences)</summary>

- FLIP_AAV | protein-site | regression
    - [FLIP_AAV_one-vs-rest](https://huggingface.co/datasets/tyang816/FLIP_AAV_one-vs-rest), [FLIP_AAV_two-vs-rest](https://huggingface.co/datasets/tyang816/FLIP_AAV_two-vs-rest), [FLIP_AAV_mut-des](https://huggingface.co/datasets/tyang816/FLIP_AAV_mut-des), [FLIP_AAV_des-mut](https://huggingface.co/datasets/tyang816/FLIP_AAV_des-mut), [FLIP_AAV_seven-vs-rest](https://huggingface.co/datasets/tyang816/FLIP_AAV_seven-vs-rest), [FLIP_AAV_low-vs-high](https://huggingface.co/datasets/tyang816/FLIP_AAV_low-vs-high), [ FLIP_AAV_sampled](https://huggingface.co/datasets/tyang816/FLIP_AAV_sampled)
- FLIP_GB1 | protein-site | regression
    - [FLIP_GB1_one-vs-rest](https://huggingface.co/datasets/tyang816/FLIP_GB1_one-vs-rest), [FLIP_GB1_two-vs-rest](https://huggingface.co/datasets/tyang816/FLIP_GB1_two-vs-rest), [FLIP_GB1_three-vs-rest](https://huggingface.co/datasets/tyang816/FLIP_GB1_three-vs-rest), [FLIP_GB1_low-vs-high](https://huggingface.co/datasets/tyang816/FLIP_GB1_low-vs-high), [FLIP_GB1_sampled](https://huggingface.co/datasets/tyang816/FLIP_GB1_sampled)
- TAPE_Fluorescence | protein-site | regression
    - [TAPE_Fluorescence](https://huggingface.co/datasets/tyang816/TAPE_Fluorescence)
- TAPE_Stability | protein-site | regression
    - [TAPE_Stability](https://huggingface.co/datasets/tyang816/TAPE_Stability)

</details>

## 📈 Supported Metrics

| Name          | Torchmetrics     | Problem Type                                            |
| ------------- | ---------------- | ------------------------------------------------------- |
| accuracy      | Accuracy         | single_label_classification/ multi_label_classification |
| recall        | Recall           | single_label_classification/ multi_label_classification |
| precision     | Precision        | single_label_classification/ multi_label_classification |
| f1            | F1Score          | single_label_classification/ multi_label_classification |
| mcc           | MatthewsCorrCoef | single_label_classification/ multi_label_classification |
| auc           | AUROC            | single_label_classification/ multi_label_classification |
| f1_max        | F1ScoreMax       | multi_label_classification                              |
| spearman_corr | SpearmanCorrCoef | regression                                              |
| mse           | MeanSquaredError | regression                                              |

## ✈️ Reuirement

### Conda Enviroment

Please make sure you have installed **[Anaconda3](https://www.anaconda.com/download)** or **[Miniconda3](https://docs.conda.io/projects/miniconda/en/latest/)**.

### Hardware

We recommend a **24GB** RTX 3090 or better, but it mainly depends on which PLM you choose.

## 🧬 Get Started

### Installation
```
1. git clone https://github.com/tyang816/VenusFactory.git
2. cd VenusFactory
3. conda create -n venus python==3.10
4. conda activate venus(windows); source activate venus(linux)
5. pip install -r ./requirements.txt
```

### Quick Start
*Fine-tuning*: Run the following scripts with different methods and adjust model parameters via ```--plm_model```.
```
Freeze: bash ./script/train/train_plm_vanilla.sh
SES-Adapter: bash ./script/train/train_plm_ses-adapter.sh
LoRA: bash ./script/train/train_plm_lora.sh
DoRA: bash ./script/train/train_plm_dora.sh
AdaLoRA: bash ./script/train/train_plm_adalora.sh
QLoRA: bash ./script/train/train_plm_qlora.sh
```
*eval*: Run following scripts to eval the trained model.
```
bash ./script/eval/eval.sh
```

### Fine-tuning with Venus Board GUI(power by Gradio)
```

```

### crawler-tools
*Download the protein sequence from uniprot*.
```
bash ./crawler/download_uniprot_seq.sh
``` 
*Download the protein structure from Alphafold or RCSB database*:
```
Alphafold: bash ./crawler/download_alphafold.sh
RCSB: bash ./crawler/download_rcsb.sh
``` 

## 🙌 Citation

Please cite our work if you have used our code or data.

```

```

## 🎊 Acknowledgement

Thanks the support of [Liang's Lab](https://ins.sjtu.edu.cn/people/lhong/index.html).