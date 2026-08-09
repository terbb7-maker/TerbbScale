alter table public.settings
  alter column scopes set default array[
    'instagram_business_basic',
    'instagram_business_content_publish',
    'instagram_business_manage_insights'
  ]::text[];

update public.settings
set scopes = array_append(scopes, 'instagram_business_manage_insights')
where not scopes @> array['instagram_business_manage_insights']::text[];
