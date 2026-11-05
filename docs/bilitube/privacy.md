---
title: bilitube privacy policy
description: What bilitube does with data from the YouTube API.
---

# bilitube privacy policy

*Last updated: 5 November 2026*

[bilitube](index.md) is a personal command-line tool, run by me, Richard van
der Oost, on my own computer, to publish videos to my own YouTube channel. It
has no other users. This policy describes what it does with data it gets
through the YouTube API Services.

## What it accesses

bilitube uses the YouTube API Services. When I sign in with my Google account
it asks for the `youtube.force-ssl` scope, and uses it only to:

- upload my own videos and set their title, description, tags and thumbnail;
- read and update the metadata of my own videos;
- list, upload and update the caption tracks on my own videos.

It does not read data about any other user, channel or video.

## What it stores

The OAuth token Google issues is stored only on my own computer, in a file
readable by my user account alone. Apart from the ID of each video I upload,
bilitube stores no data it receives from the YouTube API Services.

## What it shares

Nothing obtained from the YouTube API Services is sold, shared with or
disclosed to anyone. The tool does send my own content — the transcripts of my
own videos — to Anthropic's Claude API to clean up and translate subtitles,
and uploads my own videos to my own Bilibili channel. Neither involves data
about anyone else.

## Cookies and tracking

bilitube is a command-line tool. It sets no cookies and does no tracking or
analytics.

## Google

bilitube uses the YouTube API Services. How Google handles data is described
in the [Google Privacy Policy](https://policies.google.com/privacy). Access
can be revoked at any time on the
[Google security settings page](https://myaccount.google.com/permissions);
deleting the local token file removes everything bilitube kept.

## Contact

Questions about this policy: richard@blendergrid.com
