import json
import os
import sys
import base64
from pathlib import Path
import pandas as pd
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

def merge_and_save_tables(doc, output_dir="tables"):
    if not doc.tables:
        print("No tables found to merge.")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print("Analyzing tables for merging...")
    merged_groups = []
    
    # Get all tables as DataFrames
    dfs = [t.export_to_dataframe() for t in doc.tables]
    
    if not dfs:
        return []

    current_indices = [0]
    current_df = dfs[0]
    
    for i in range(1, len(dfs)):
        next_df = dfs[i]
        
        # Simple heuristic: Merge if column count matches
        if len(current_df.columns) == len(next_df.columns):
            # Check if headers match
            if list(current_df.columns) == list(next_df.columns):
                # Headers match, probably repeated header on next page. 
                # Just concat.
                current_df = pd.concat([current_df, next_df], ignore_index=True)
                print(f"  Merged table {i} into previous table (matching headers).")
            else:
                # Headers do not match. 
                # It's likely that next_df has the first row of data as header 
                # OR it has integer headers.
                
                # Check if columns are just a RangeIndex (0, 1, 2...)
                is_range_index = isinstance(next_df.columns, pd.RangeIndex) or \
                                 (pd.api.types.is_numeric_dtype(next_df.columns) and 
                                  list(next_df.columns) == list(range(len(next_df.columns))))
                
                if is_range_index:
                     # Just rename columns to match the previous table
                     next_df.columns = current_df.columns
                     current_df = pd.concat([current_df, next_df], ignore_index=True)
                     print(f"  Merged table {i} into previous table (renamed integer columns).")
                else:
                    # The columns are likely data because they are strings/mixed but don't match previous header.
                    # We need to turn the header into a row.
                    
                    # 1. Convert headers to a list (this is our "lost" row)
                    header_row = next_df.columns.tolist()
                    
                    # 2. Get the rest of the data
                    data_values = next_df.values.tolist()
                    
                    # 3. Combine them
                    full_data = [header_row] + data_values
                    
                    # 4. Create new DF with the correct columns from current_df
                    fixed_next_df = pd.DataFrame(full_data, columns=current_df.columns)
                    
                    current_df = pd.concat([current_df, fixed_next_df], ignore_index=True)
                    print(f"  Merged table {i} into previous table (recovered header as data row).")

            current_indices.append(i)
        else:
            merged_groups.append({'indices': current_indices, 'df': current_df})
            current_indices = [i]
            current_df = next_df
            
    merged_groups.append({'indices': current_indices, 'df': current_df})

    # Save merged tables
    for i, group in enumerate(merged_groups):
        csv_path = f"{output_dir}/merged_table_{i+1}.csv"
        group['df'].to_csv(csv_path, index=False)
        print(f"  Saved {csv_path}")
        
    return merged_groups

def generate_merged_markdown(doc, md_text, merged_groups):
    print("Post-processing Markdown to merge tables...")
    
    # We need to process groups in order to safely use replace(..., 1)
    # But we must be careful: if we replace Table 1 with MergedTable, 
    # and later we try to find Table 1 again, it's gone. That's fine.
    # The risk is if Table 2 text is identical to Table 1 text, but we only merged Table 1.
    # However, 'merged_groups' covers ALL tables.
    
    for group in merged_groups:
        indices = group['indices']
        if len(indices) <= 1:
            # No merge happened for this table, skipping replacement
            # (or we could assume the original MD is correct for single tables)
            continue
            
        merged_df = group['df']
        # Convert merged DF to markdown
        # Docling/Pandas markdown format might differ slightly, but standard pipe tables are usually compatible.
        merged_md_table = merged_df.to_markdown(index=False)
        
        # Replace the first table's content with the merged table
        first_idx = indices[0]
        first_table_item = doc.tables[first_idx]
        first_table_md_snippet = first_table_item.export_to_markdown()
        
        # We replace only the first occurrence found.
        # Ideally, we would track position, but simple replacement is the best heuristic available.
        if first_table_md_snippet in md_text:
            md_text = md_text.replace(first_table_md_snippet, merged_md_table, 1)
        else:
            print(f"  Warning: Could not find original text for table {first_idx} in Markdown.")

        # Remove subsequent tables
        for idx in indices[1:]:
            table_item = doc.tables[idx]
            table_md_snippet = table_item.export_to_markdown()
            
            if table_md_snippet in md_text:
                # Replace with empty string or a placeholder
                # We use a newline to prevent gluing text together awkwardly
                md_text = md_text.replace(table_md_snippet, "\n<!-- merged table part -->\n", 1)
            else:
                print(f"  Warning: Could not find original text for table {idx} in Markdown.")
                
    return md_text

def parse_pdf(file_path="file.pdf", output_path="output.json", images_folder="images/"):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    try:
        print(f"Processing {file_path} with Docling...")
        pdf_pipeline_options = PdfPipelineOptions(generate_picture_images=True, generate_page_images=True)
        pdf_format_option = PdfFormatOption(pipeline_options=pdf_pipeline_options)
        converter = DocumentConverter(format_options={InputFormat.PDF: pdf_format_option})
        result = converter.convert(file_path)
        
        # Serialize the document to a dictionary
        doc_data = result.document.export_to_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(doc_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved parsed data to {output_path}")

        # Merge tables first to get the groups
        merged_groups = merge_and_save_tables(result.document)

        # Generate original markdown
        original_md = result.document.export_to_markdown()
        
        # Save figures first to get filenames
        Path(images_folder).mkdir(parents=True, exist_ok=True)
        saved_image_paths = []
        
        if hasattr(result.document, 'pictures') and result.document.pictures:
            print(f"Saving {len(result.document.pictures)} pictures to {images_folder}...")
            for i, picture in enumerate(result.document.pictures):
                if hasattr(picture, 'image') and hasattr(picture.image, 'pil_image') and picture.image.pil_image:
                    try:
                        pil_image = picture.image.pil_image
                        image_format = "png" # Default format
                        if hasattr(picture.image, 'mimetype') and picture.image.mimetype:
                            # Extract format from mimetype, e.g., 'image/jpeg' -> 'jpeg'
                            image_format = picture.image.mimetype.split('/')[-1].lower()
                        
                        picture_filename = f"picture_{i}.{image_format}"
                        picture_path = Path(images_folder) / picture_filename
                        
                        pil_image.save(picture_path, format=image_format.upper()) # PIL needs uppercase format
                        print(f"  Saved {picture_filename}")
                        saved_image_paths.append(f"{images_folder}{picture_filename}")
                    except Exception as e:
                        print(f"  Could not save picture {i} (ID: {getattr(picture, 'id', 'N/A')}): {e}")
                        saved_image_paths.append(None) # Keep index sync
                else:
                    print(f"  Picture {i} (ID: {getattr(picture, 'id', 'N/A')}) has no PIL image data (image.pil_image attribute is missing or empty).")
                    saved_image_paths.append(None)
        else:
            print("No pictures found in the document.")

        # Post-process markdown to merge tables
        final_md = generate_merged_markdown(result.document, original_md, merged_groups)

        # Replace <!-- image --> with actual image links
        if saved_image_paths:
            print("Injecting image links into Markdown...")
            for img_path in saved_image_paths:
                if img_path:
                    # Replace the first occurrence of <!-- image --> with the image link
                    if "<!-- image -->" in final_md:
                         final_md = final_md.replace("<!-- image -->", f"![Image]({img_path})", 1)
                    else:
                        print(f"  Warning: No placeholder found for image {img_path}")
                else:
                    # If image wasn't saved, just remove one placeholder if present?
                    # Or keep it as a comment? Let's keep it but maybe mark it.
                    # For now, let's just consume the placeholder to keep sync
                     if "<!-- image -->" in final_md:
                         final_md = final_md.replace("<!-- image -->", "<!-- image missing -->", 1)

        # Export to Markdown
        md_output_path = "output.md"
        with open(md_output_path, 'w', encoding='utf-8') as f:
            f.write(final_md)
        print(f"Successfully saved merged markdown to {md_output_path}")

    except Exception as e:
        print(f"An error occurred: {e}")
        # traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    parse_pdf()
