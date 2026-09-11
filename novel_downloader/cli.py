import sys
from scripts.download import download_novel, argparse

def main():
    parser = argparse.ArgumentParser(description="Novel Downloader CLI")
    parser.add_argument("novel_name", help="Name of the novel to search and download")
    parser.add_argument("--output-dir", default="./downloads", help="Directory to save the novel txt")
    args = parser.parse_args()

    success = download_novel(args.novel_name, args.output_dir)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
