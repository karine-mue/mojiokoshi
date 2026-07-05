select
  id,
  status,
  failure_stage,
  exit_code,
  run_id,
  coalesce(app_version, 'pre-0.1') as app_version,
  run_label,
  audio_file,
  source_language,
  language_arg,
  detected_language,
  round(language_probability, 4) as lang_prob,
  round(elapsed_sec, 2) as elapsed,
  segment_count,
  transcript_chars
from transcribe_runs
where coalesce(is_deleted, 0) = 0
order by id desc
limit 20;
