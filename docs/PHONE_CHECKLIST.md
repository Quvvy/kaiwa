# Phone access: real-device checklist

The automated checks can't cover a real iPhone or a real reboot. Run these on the PC and iPhone, and note anything that doesn't match.

## Setup
- [ ] Settings → Phone shows the setup commands. After running them, the page moves on by itself.
- [ ] Turn on: if Tailscale asks you to approve HTTPS, the page opens or links to it, then moves on by itself once approved.
- [ ] Scan the first QR code, install Tailscale, sign in, tap Allow. The page moves on by itself.
- [ ] Scan the second QR code. Kaiwa opens in Safari and shows the Add to Home Screen tip.
- [ ] Add it to the home screen. The icon looks right, and it opens with no Safari bars.

## Using it (Wi-Fi off, on mobile data)
- [ ] First hold-to-talk: the mic prompt appears. After allowing, it says the mic is on.
- [ ] Holding the button doesn't select text or scroll the page, and the bar turns red.
- [ ] A recording is understood, in both a lesson and Chat.
- [ ] Replies play by themselves without a tap, at normal volume, from the speaker rather than the earpiece.
- [ ] Chat replies arrive sentence by sentence, not all at once at the end.
- [ ] Tapping into a text box doesn't zoom the page.
- [ ] Nothing is hidden behind the notch or the home bar.
- [ ] Settings has no Push-to-talk, API key, Updates or Phone sections.
- [ ] Progress made on the phone shows up on the PC, and the other way round.

## Everyday friction
- [ ] Force-quit the app and reopen it three times. How many mic prompts did you get?
- [ ] Leave it overnight, then tap the icon. Does it connect without opening Tailscale?

## When things go wrong
- [ ] `systemctl --user stop kaiwa-phone`: the phone shows "Can't reach your PC".
- [ ] `systemctl --user start kaiwa-phone`: the phone recovers by itself.
- [ ] Turn off Tailscale on the phone: same screen, and it recovers when turned back on.

## The PC
- [ ] Close the Kaiwa window: the phone keeps working (a short gap is expected the first time).
- [ ] Reopen the window: it attaches straight away, with no port error.
- [ ] Restart the PC and don't sign in: the phone still works.
- [ ] Leave the PC idle past KDE's suspend timer: it stays awake.
- [ ] Choose Sleep yourself: it still sleeps.
- [ ] Turn off phone access: the phone can't reach Kaiwa, and after closing the window nothing is left running (`systemctl --user status kaiwa-phone`).
