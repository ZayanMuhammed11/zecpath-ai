"""
Batch Processor for Zecpath AI hiring platform.
Processes single or multiple JD text files through the JDParser pipeline.
"""

import os
import json
import time

from ats_engine.jd_parser import JDParser
from utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_FOLDER = os.path.join("data", "jd_parsed")


class BatchProcessor:
    """
    Processes job description text files individually or in bulk.
    Saves parsed JSON output to data/jd_parsed/ folder.
    """

    def __init__(self):
        """Initialize BatchProcessor with a JDParser instance."""
        self.parser = JDParser()
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        logger.info(f"BatchProcessor initialized. Output folder: {OUTPUT_FOLDER}")

    def process_single(self, file_path: str) -> dict:
        """
        Parse a single JD text file and save the output as JSON.

        Args:
            file_path: Path to the .txt JD file.

        Returns:
            Parsed and validated JobProfile dict.

        Raises:
            Does not raise — errors are logged and re-raised for batch tracking.
        """
        logger.info(f"Processing single file: {file_path}")

        # Read the JD text file
        with open(file_path, "r", encoding="utf-8") as f:
            jd_text = f.read()

        # Generate job_id from filename
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        job_id = "JOB-" + base_name.upper()
        logger.info(f"Generated job_id: {job_id}")

        # Parse the JD
        parsed = self.parser.parse(jd_text, job_id)

        # Save output JSON
        output_file = os.path.join(OUTPUT_FOLDER, base_name + ".json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Output saved to: {output_file}")
        return parsed

    def process_batch(self, folder_path: str) -> dict:
        """
        Process all .txt JD files in a folder and return a summary report.

        Args:
            folder_path: Path to folder containing .txt JD files.

        Returns:
            Summary dict with total, successful, failed counts and output folder.
        """
        logger.info(f"Starting batch processing for folder: {folder_path}")

        txt_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(".txt")
        ]

        total = len(txt_files)
        successful = 0
        failed = 0
        failed_files = []

        logger.info(f"Found {total} .txt files to process.")

        for index, filename in enumerate(txt_files, start=1):
            file_path = os.path.join(folder_path, filename)
            print(f"Processing {index}/{total}: {filename}")
            logger.info(f"Processing {index}/{total}: {filename}")

            try:
                self.process_single(file_path)
                successful += 1
                logger.info(f"Successfully processed: {filename}")
            except Exception as e:
                failed += 1
                failed_files.append(filename)
                logger.error(f"Failed to process '{filename}': {e}")

            # Rate limit buffer between API calls
            if index < total:
                time.sleep(5)

        summary = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "failed_files": failed_files,
            "output_folder": OUTPUT_FOLDER,
        }

        logger.info(f"Batch processing complete: {summary}")
        print(f"\nBatch complete: {successful}/{total} succeeded, {failed} failed.")
        return summary