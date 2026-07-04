select
  id,
  run_id,
  run_user,
  run_host,
  run_label,
  audio_file,
  source_language,
  language_arg,
  detected_language,
  round(language_probability, 4) as lang_prob,
  round(duration_sec, 2) as duration,
  round(elapsed_sec, 2) as elapsed,
  segment_count,
  transcript_chars,
  output_dir
from transcribe_runs
where coalesce(is_deleted, 0) = 0
order by id;