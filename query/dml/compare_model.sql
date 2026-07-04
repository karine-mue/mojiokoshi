-- query/dml/compare_model.sql
select
  experiment_name,
  source_language,
  model,
  language_arg,
  detected_language,
  round(avg(language_probability), 4) as avg_lang_prob,
  round(avg(duration_sec), 2) as avg_duration,
  round(avg(elapsed_sec), 2) as avg_elapsed,
  round(avg(duration_sec / elapsed_sec), 2) as realtime_factor,
  round(avg(segment_count), 1) as avg_segments,
  round(avg(transcript_chars), 1) as avg_chars,
  count(*) as run_count
from transcribe_runs
where coalesce(is_deleted, 0) = 0
  and coalesce(status, 'success') = 'success'
group by
  experiment_name,
  source_language,
  model,
  language_arg,
  detected_language
order by
  experiment_name,
  source_language,
  model,
  language_arg;
