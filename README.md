# What can this script do

It takes your Google export and fixes date on each photo.

After you download your photos from Google Photos using
Takeout service, they all are missing proper timestmps.
When imported to Apple Photos the dates are incorrect.

This script reads metadata delivered with the photos and
applies date to each photo.

In case where metadata is missing date is estimated
based on other photos in the directory.

I have written and used this script to move pictures from
Google Photos into Apple Photos.

## How take your photos from Google

Step by step instructions:

1. Export pictures using <https://takeout.google.com>.
2. Export can take a long time, even days when you are using Advanced Protection Program.
3. Extract all photos into single directory.
4. Run the script `python3 photo_sync.py <path_to_photos>`.
5. Upload photos to other service, or keep them yourself.
