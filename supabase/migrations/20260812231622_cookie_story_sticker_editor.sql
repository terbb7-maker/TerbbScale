alter table public.cookie_story_presets
  add column sticker_x double precision not null default 0.5,
  add column sticker_y double precision not null default 0.81,
  add column sticker_width double precision not null default 0.58,
  add column sticker_height double precision not null default 0.1,
  add column sticker_rotation double precision not null default 0,
  add column sticker_font_size integer not null default 14,
  add column sticker_font_family text not null default 'Inter',
  add column sticker_italic boolean not null default false,
  add column sticker_text_color text not null default '#ffffff',
  add column sticker_background_color text not null default 'rgba(0, 0, 0, 0.6)';

alter table public.cookie_story_presets
  add constraint cookie_story_presets_sticker_size_check
    check (sticker_width between 0.08 and 0.9 and sticker_height between 0.04 and 0.3),
  add constraint cookie_story_presets_sticker_position_check
    check (
      sticker_x between sticker_width / 2 and 1 - sticker_width / 2
      and sticker_y between sticker_height / 2 and 1 - sticker_height / 2
    ),
  add constraint cookie_story_presets_sticker_rotation_check
    check (sticker_rotation between -180 and 180),
  add constraint cookie_story_presets_sticker_font_size_check
    check (sticker_font_size between 14 and 32),
  add constraint cookie_story_presets_sticker_font_family_check
    check (sticker_font_family in (
      'Inter', 'Roboto', 'Poppins', 'Montserrat', 'Bebas Neue',
      'Playfair Display', 'Merriweather', 'Pacifico', 'DancingScript',
      'Anton', 'Lora', 'Great Vibes'
    )),
  add constraint cookie_story_presets_sticker_text_color_check
    check (sticker_text_color in (
      '#ffffff', 'rgba(0, 0, 0, 1)', 'rgba(65, 174, 69, 1)',
      'rgba(0, 212, 255, 1)', 'rgba(53, 141, 255, 1)',
      'rgba(115, 0, 255, 1)', 'rgba(255, 255, 255, 1)',
      'rgba(255, 192, 10, 1)', 'rgba(255, 129, 0, 1)',
      'rgba(255, 49, 49, 1)', 'rgba(255, 101, 195, 1)'
    )),
  add constraint cookie_story_presets_sticker_background_color_check
    check (sticker_background_color in (
      'rgba(0, 0, 0, 0.6)', 'rgba(0, 0, 0, 1)', 'rgba(65, 174, 69, 1)',
      'rgba(0, 212, 255, 1)', 'rgba(53, 141, 255, 1)',
      'rgba(115, 0, 255, 1)', 'rgba(255, 255, 255, 1)',
      'rgba(255, 192, 10, 1)', 'rgba(255, 129, 0, 1)',
      'rgba(255, 49, 49, 1)', 'rgba(255, 101, 195, 1)'
    ));
