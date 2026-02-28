"""Build the HTML email digest."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from config import SITE_URL


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _format_time(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%b %d, %I:%M %p UTC")


def _build_team_section(team: dict, headlines: list[dict], videos: list[dict]) -> str:
    """Build the HTML section for one team."""
    primary = team["primary_color"]
    secondary = team["secondary_color"]
    text_color = team["text_color"]
    logo_url = team["logo_url"]
    name = _escape(team["name"])

    # --- Header with gradient, logo, and team name ---
    header = f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:24px;">
      <tr>
        <td style="background: linear-gradient(135deg, {primary}, {secondary}); padding: 16px 20px; border-radius: 8px 8px 0 0;">
          <table cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align: middle; padding-right: 14px;">
                <img src="{logo_url}" alt="{name}" width="44" height="44"
                     style="display:block; border-radius: 4px; background: #fff; padding: 2px;" />
              </td>
              <td style="vertical-align: middle;">
                <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 22px; font-weight: 700; color: {text_color}; letter-spacing: 0.5px;">
                  {name}
                </span>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """

    # --- Headlines ---
    headlines_html = ""
    if headlines:
        items = ""
        for i, h in enumerate(headlines, 1):
            title = _escape(h["title"])
            url = _escape(h["url"])
            source = _escape(h.get("source", ""))
            time_str = _format_time(h.get("published"))
            source_badge = f'<span style="color: #888; font-size: 12px; font-weight: 400;"> &mdash; {source}</span>' if source else ""
            time_badge = f'<span style="color: #aaa; font-size: 11px; display: block; margin-top: 2px;">{time_str}</span>' if time_str else ""

            items += f"""
            <tr>
              <td style="padding: 10px 16px; border-bottom: 1px solid #f0f0f0;">
                <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; font-weight: 700; color: {primary}; margin-right: 6px;">{i}.</span>
                <a href="{url}" style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 15px; color: #1a1a1a; text-decoration: none; font-weight: 500;" target="_blank">{title}</a>
                {source_badge}
                {time_badge}
              </td>
            </tr>
            """

        headlines_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #ffffff; border-left: 1px solid #e8e8e8; border-right: 1px solid #e8e8e8;">
          <tr>
            <td style="padding: 12px 16px 4px 16px;">
              <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 13px; font-weight: 700; color: #666; text-transform: uppercase; letter-spacing: 1px;">Headlines</span>
            </td>
          </tr>
          {items}
        </table>
        """
    else:
        headlines_html = """
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #ffffff; border-left: 1px solid #e8e8e8; border-right: 1px solid #e8e8e8;">
          <tr>
            <td style="padding: 16px; color: #999; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px; font-style: italic;">
              No recent headlines found.
            </td>
          </tr>
        </table>
        """

    # --- YouTube Videos ---
    videos_html = ""
    if videos:
        video_cards = ""
        for v in videos:
            title = _escape(v["title"])
            url = _escape(v["url"])
            thumbnail = _escape(v["thumbnail"])

            video_cards += f"""
            <tr>
              <td style="padding: 8px 16px;">
                <a href="{url}" style="text-decoration: none;" target="_blank">
                  <table cellpadding="0" cellspacing="0" border="0" width="100%">
                    <tr>
                      <td width="160" style="vertical-align: top;">
                        <div style="position: relative; display: inline-block;">
                          <img src="{thumbnail}" alt="{title}" width="152" height="86"
                               style="display: block; border-radius: 6px; object-fit: cover; border: 1px solid #e0e0e0;" />
                          <!-- Play button overlay -->
                          <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 36px; height: 36px; background: rgba(0,0,0,0.7); border-radius: 50%; text-align: center; line-height: 36px;">
                            <span style="color: #fff; font-size: 16px; margin-left: 2px;">&#9654;</span>
                          </div>
                        </div>
                      </td>
                      <td style="vertical-align: top; padding-left: 12px;">
                        <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 14px; color: #1a1a1a; font-weight: 500; line-height: 1.4;">
                          {title}
                        </span>
                        <br/>
                        <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; color: #cc0000; font-weight: 600; margin-top: 4px; display: inline-block;">
                          &#9654; Watch on YouTube
                        </span>
                      </td>
                    </tr>
                  </table>
                </a>
              </td>
            </tr>
            """

        videos_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #ffffff; border-left: 1px solid #e8e8e8; border-right: 1px solid #e8e8e8;">
          <tr>
            <td style="padding: 12px 16px 4px 16px;">
              <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 13px; font-weight: 700; color: #666; text-transform: uppercase; letter-spacing: 1px;">Videos</span>
            </td>
          </tr>
          {video_cards}
        </table>
        """

    # --- Bottom border ---
    bottom = f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="height: 4px; background: linear-gradient(135deg, {primary}, {secondary}); border-radius: 0 0 8px 8px;"></td>
      </tr>
    </table>
    """

    return header + headlines_html + videos_html + bottom


def build_email(team_data: list[dict], subscriber_email: str = "") -> str:
    """Build the full HTML email.

    Args:
        team_data: list of dicts with keys: team, headlines, videos
        subscriber_email: subscriber's email for unsubscribe link

    Returns:
        Complete HTML string for the email.
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%B %d, %Y at %I:%M %p UTC")

    sections = ""
    for td in team_data:
        sections += _build_team_section(td["team"], td["headlines"], td["videos"])

    # Build footer with unsubscribe + manage links
    unsubscribe_url = f"{SITE_URL}/unsubscribe.html?email={quote(subscriber_email)}" if subscriber_email else ""
    manage_url = f"{SITE_URL}/"

    footer_links = ""
    if subscriber_email:
        footer_links = f"""
              <p style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; color: #bbb; margin: 8px 0 0 0;">
                <a href="{manage_url}" style="color: #999; text-decoration: underline;">Manage your teams</a>
                &nbsp;&bull;&nbsp;
                <a href="{unsubscribe_url}" style="color: #999; text-decoration: underline;">Unsubscribe</a>
              </p>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sports Digest</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f7; -webkit-font-smoothing: antialiased;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f7;">
    <tr>
      <td align="center" style="padding: 24px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%;">

          <!-- Master Header -->
          <tr>
            <td style="text-align: center; padding: 20px 0 8px 0;">
              <h1 style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 28px; font-weight: 800; color: #1a1a1a; margin: 0; letter-spacing: -0.5px;">
                &#9917; Sports Digest
              </h1>
              <p style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 13px; color: #888; margin: 6px 0 0 0;">
                {timestamp}
              </p>
            </td>
          </tr>

          <!-- Team Sections -->
          <tr>
            <td>
              {sections}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="text-align: center; padding: 28px 0 12px 0;">
              <p style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11px; color: #bbb; margin: 0;">
                Generated automatically &bull; FanFeeder Sports Digest
              </p>
              {footer_links}
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
