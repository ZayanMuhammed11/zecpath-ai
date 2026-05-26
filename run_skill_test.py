from parsers import segment_resume
from ats_engine.skill_extractor import SkillExtractor

# Use a real cleaned resume txt from data/
with open("data/qe_sample_resume.txt", encoding="utf-8") as f:
    text = f.read()

segmented = segment_resume(text, candidate_id="TEST-001")
extractor = SkillExtractor()
skills = extractor.extract(segmented, top_n=20)

for s in skills:
    print(s)