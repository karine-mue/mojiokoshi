select
  id,
  coalesce(is_deleted, 0) as is_deleted,
  deleted_at,
  delete_reason,
  status,
  failure_stage,
  exit_code,
  replace(replace(substr(coalesce(error_message, ''), 1, 80), char(10), ' '), char(13), ' ') as error_message,
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
order by id;
