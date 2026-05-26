from parsers import extract_resume_text

result = extract_resume_text(
    file_path="data/resume2.pdf",
    save_output=True,
    output_dir="data"
)

print("=== EXTRACTION COMPLETE ===")
print(f"Characters extracted: {len(result)}")
print("\n=== FIRST 500 CHARACTERS ===")
print(result[:50000])