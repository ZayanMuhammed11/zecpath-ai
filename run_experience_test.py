from parsers import segment_resume
from ats_engine.experience_parser import ExperienceParser

with open("data/qe_sample_resume.txt", encoding="utf-8") as f:
    text = f.read()

segmented = segment_resume(text, candidate_id="QE-001")
parser = ExperienceParser()

experiences = parser.parse(segmented, use_llm=False)
for e in experiences:
    print(e)

gaps = parser.detect_gaps(experiences)
print("\nGaps:", gaps)

relevance = parser.calculate_relevance_score(
    experiences, "quality engineer"
)
print("\nRelevance:", relevance)