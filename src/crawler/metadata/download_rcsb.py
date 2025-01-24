import requests
import json
import os
import argparse
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_metadata_from_rcsb(pdb):
    template_file_path = "download/rcsb_query_template.txt"
    with open(template_file_path, 'r') as file:
        query_template = file.read()
    
    variables = {"id": pdb}
    message = f"{pdb} successfully downloaded"
    url = "https://data.rcsb.org/graphql"
    
    response = requests.post(url, json={'query': query_template, 'variables': variables})

    if response.status_code == 200:
        result = response.json()
    else:
        message = f"{pdb} failed to download"
        return None, message
    
    if not result["data"]["entry"]:
        message = f"{pdb} failed to download"
        return None, message
    
    return result, message


def download_single_pdb(pdb_id, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    output_file = os.path.join(out_dir, f"{pdb_id}.json")
    
    if os.path.exists(output_file):
        return f"Skipping {pdb_id}, already exists"
        
    result, message = get_metadata_from_rcsb(pdb_id)
    if result is None:
        return message
        
    with open(output_file, 'w') as f:
        json.dump(result, f)
    return message


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdb_id_file", type=str, default=None)
    parser.add_argument("--pdb_id", type=str, default=None)
    parser.add_argument("--error_file", type=str, default=None)
    parser.add_argument("--out_dir", type=str, required=True)
    parser.add_argument("--num_workers", type=int, default=12)
    
    args = parser.parse_args()
    
    if not args.pdb_id and not args.pdb_id_file:
        print("Error: Must provide either pdb_id or pdb_id_file")
        exit(1)
    
    os.makedirs(args.out_dir, exist_ok=True)
    downloaded_pdbs = [p[:4] for p in os.listdir(args.out_dir)]
    error_proteins = []
    error_messages = []
    
    if args.pdb_id_file:
        pdbs = open(args.pdb_id_file, 'r').read().splitlines()
        
        def download_pdb_metadata(pdb_id, downloaded_pdbs, args):
            if pdb_id in downloaded_pdbs:
                return pdb_id, f"{pdb_id} already exists, skipping"
            result, message = get_metadata_from_rcsb(pdb_id)
            if result is None:
                return pdb_id, message
            with open(os.path.join(args.out_dir, f"{pdb_id}.json"), 'w') as f:
                json.dump(result, f)
            return pdb_id, message
        
        with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
            future_to_pdb = {executor.submit(download_pdb_metadata, pdb_id, downloaded_pdbs, args): pdb_id for pdb_id in pdbs}

            with tqdm(total=len(pdbs), desc="Downloading PDB Metadata") as bar:
                for future in as_completed(future_to_pdb):
                    pdb_id, message = future.result()
                    bar.set_description(message)
                    if "failed" in message:
                        error_proteins.append(pdb_id)
                        error_messages.append(message)
                    bar.update(1)
        
    elif args.pdb_id:
        message = download_single_pdb(args.pdb_id, args.out_dir)
        print(message)
        if "failed" in message:
            error_proteins.append(args.pdb_id)
            error_messages.append(message)
    
    if error_proteins and args.error_file:
        error_dict = {"protein": error_proteins, "error": error_messages}
        error_file_dir = os.path.dirname(args.error_file)
        os.makedirs(error_file_dir, exist_ok=True)
        pd.DataFrame(error_dict).to_csv(args.error_file, index=False)