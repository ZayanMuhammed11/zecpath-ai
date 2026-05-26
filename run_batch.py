from ats_engine.batch_processor import BatchProcessor

bp = BatchProcessor()
summary = bp.process_batch("data/jd")
print(summary)