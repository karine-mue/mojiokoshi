select
  source_language,
  language_arg,
  detected_language,
  round(avg(language_probability), 4) as avg_lang_prob,
  round(avg(elapsed_sec), 2) as avg_elapsed,
  round(avg(segment_count), 1) as avg_segments,
  round(avg(transcript_chars), 1) as avg_chars,
  count(*) as run_count
from transcribe_runs
where experiment_name = 'l0opback_lang_compare'
  and coalesce(is_deleted, 0) = 0
group by
  source_language,
  language_arg,
  detected_language
order by
  source_language,
  language_arg,
  detected_language;