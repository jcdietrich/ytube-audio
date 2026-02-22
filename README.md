# yt-dlp Audio Player for Home Assistant

A Home Assistant custom integration that allows you to play audio from **YouTube, SoundCloud, Vimeo, Bandcamp, and 1000+ other sites** on your media players using yt-dlp.

## Features

- **1000+ supported sites** - YouTube, SoundCloud, Vimeo, Bandcamp, Twitch, and more
- **Multiple media players** - play on one or multiple players simultaneously
- **Group support** - works with media player groups
- **Proxy streaming** - streams through Home Assistant to avoid 403 errors
- **Voice control** - Assist integration for voice commands
- **Media browser** - browse and play from the HA media browser
- **Seeking support** - seek to any position in the audio
- **Format selection** - choose between M4A, MP3, Opus, or best quality
- **No downloads** - streams audio directly without downloading files

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Add"
7. Search for "YouTube Audio Player" and install it
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ytube_audio` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "YouTube Audio Player"
4. Follow the setup wizard

## Usage

### Service: `ytube_audio.play_audio`

Play audio from a YouTube video on one or more media players.

#### Service Data

| Field          | Required | Description                                                    |
|----------------|----------|----------------------------------------------------------------|
| `url`          | Yes      | YouTube video URL or video ID                                  |
| `media_player` | Yes      | Entity ID(s) of media player(s)                                |
| `proxy`        | No       | Stream through HA to avoid 403 errors (default: `true`)        |

#### Examples

**Play on a single media player:**

```yaml
service: ytube_audio.play_audio
data:
  url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  media_player: media_player.living_room_speaker
```

**Play on multiple media players:**

```yaml
service: ytube_audio.play_audio
data:
  url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  media_player:
    - media_player.living_room_speaker
    - media_player.kitchen_speaker
    - media_player.bedroom_speaker
```

**Using just a video ID:**

```yaml
service: ytube_audio.play_audio
data:
  url: "dQw4w9WgXcQ"
  media_player: media_player.living_room_speaker
```

### Automation Example

```yaml
automation:
  - alias: "Play morning music"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: ytube_audio.play_audio
        data:
          url: "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
          media_player: media_player.bedroom_speaker
```

### Script Example

```yaml
script:
  play_relaxing_music:
    alias: "Play Relaxing Music"
    sequence:
      - service: ytube_audio.play_audio
        data:
          url: "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
          media_player: media_player.living_room_speaker
```

## Supported Sites

This integration supports **1000+ sites** via yt-dlp. Some popular examples:

| Site | Example URL |
|------|-------------|
| YouTube | `https://www.youtube.com/watch?v=VIDEO_ID` |
| YouTube Music | `https://music.youtube.com/watch?v=VIDEO_ID` |
| SoundCloud | `https://soundcloud.com/artist/track` |
| Vimeo | `https://vimeo.com/VIDEO_ID` |
| Bandcamp | `https://artist.bandcamp.com/track/song` |
| Twitch | `https://www.twitch.tv/videos/VIDEO_ID` |
| Mixcloud | `https://www.mixcloud.com/user/mix/` |
| Dailymotion | `https://www.dailymotion.com/video/VIDEO_ID` |

For a full list, see [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Requirements

- Home Assistant 2024.1.0 or newer
- Media player(s) that support playing audio URLs
- Internet connection

## Troubleshooting

### Audio doesn't play

1. **Check media player compatibility** - Ensure your media player supports playing audio URLs. Some players (like Chromecast, Sonos, etc.) work well, while others may have limitations.

2. **Check the logs** - Enable debug logging to see detailed information:

   ```yaml
   logger:
     default: info
     logs:
       custom_components.ytube_audio: debug
   ```

3. **URL expiration** - YouTube audio URLs expire after some time. If playback fails, try the service call again to get a fresh URL.

### 403 Forbidden Errors

If some media players work but others get 403 errors, this is due to YouTube's IP-based URL restrictions. The extracted audio URLs are signed for Home Assistant's IP address, and some media players fetch from a different IP.

**Solution:** Enable proxy mode (enabled by default). This streams the audio through Home Assistant, ensuring the same IP is used:

```yaml
service: ytube_audio.play_audio
data:
  url: "https://www.youtube.com/watch?v=VIDEO_ID"
  media_player: media_player.problematic_player
  proxy: true
```

If you want to disable proxy for players that work without it (slightly lower latency):

```yaml
service: ytube_audio.play_audio
data:
  url: "https://www.youtube.com/watch?v=VIDEO_ID"
  media_player: media_player.local_chromecast
  proxy: false
```

### yt-dlp errors

If you see errors related to yt-dlp, try updating it:

```bash
pip install --upgrade yt-dlp
```

## Known Limitations

- **URL expiration** - Extracted audio URLs are temporary and expire after some time
- **Age-restricted videos** - May not work with age-restricted content
- **Live streams** - Limited support for live streams
- **Playlists** - Currently only supports single videos (playlist support planned)

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
