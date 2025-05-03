"""
Script to train the chatbot by creating the vector database.
This will process all markdown files in the data directory and create a Chroma database.
"""

import os
import sys
from create_database import generate_data_store

def main():
    # Check if the data directory exists
    data_dir = "./data"
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found!")
        print("Please create this directory and add your .md files there.")
        sys.exit(1)
        
    # Check if there are markdown files in the data directory
    md_files = [f for f in os.listdir(data_dir) if f.endswith(".md")]
    if not md_files:
        print(f"Error: No markdown (.md) files found in '{data_dir}'!")
        print("Please add your training data as markdown files.")
        sys.exit(1)
        
    print(f"Found {len(md_files)} markdown files to process.")
    
    # Run the training process
    print("Starting training process...")
    try:
        generate_data_store()
        print("\n✅ Training completed successfully!")
        print("Your chatbot is now ready to use.")
        print("\nTo start the API server: python run.py")
        print("To start the chat UI: streamlit run client/chat_ui.py")
    except Exception as e:
        print(f"❌ Error during training: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
