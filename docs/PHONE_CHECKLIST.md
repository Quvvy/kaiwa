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

## Windows
Install `KaiwaSetup-*.exe` from the release. Pushing a `v*` tag builds it on GitHub's Windows machines (`.github/workflows/release.yml`); `.\scripts\build_installer.ps1` builds it on a local Windows PC.

Setup, ideally on an account with no Tailscale yet:
- [ ] Settings → Phone: **Install Tailscale** asks for permission once, then the page moves on by itself.
- [ ] **Sign in to Tailscale** opens the sign-in page, then the page moves on by itself.
- [ ] **Turn on** opens the approval page. Does the wording in the wizard match what it shows?
- [ ] **Email them to myself** opens a draft with working links. **Copy them** works too.
- [ ] Complete the iPhone part from the email alone, without looking at the PC.

The tray:
- [ ] Close the window: no error, a tray icon appears, and the phone keeps working.
- [ ] Hold the push-to-talk key with the window closed: nothing records.
- [ ] Double-click the tray icon, and separately click the Start Menu icon: the window comes back within a second or two, and push-to-talk works again.
- [ ] Tray → Quit: everything stops, including `python` and the voice engine in Task Manager.
- [ ] With phone access off, closing the window quits Kaiwa as before, with no tray icon.

Restarts and sleep:
- [ ] Restart Windows from the Start Menu: nothing blocks the shutdown ("this app is preventing…").
- [ ] After signing in: no window appears, the tray icon is there, and the phone works.
- [ ] Leave it idle past the sleep timer on mains power: it stays awake. Screen-off is fine.
- [ ] On a laptop, on battery: it's allowed to sleep.
- [ ] End `python.exe` in Task Manager: the phone recovers by itself within about a minute and a half.

Updates and removal:
- [ ] Settings → About → Install update with phone access on: Kaiwa quits and Setup can finish.
- [ ] Run Setup by hand while Kaiwa is in the tray. Does it close Kaiwa, or at least say what to do?
- [ ] Turn off phone access: the phone is cut off, and the `Kaiwa` entry is gone from Task Manager → Startup apps.
- [ ] Uninstall with phone access on: the startup entry is gone.

Then do the sections above on the iPhone again, on his voice if you can. The speech thresholds were tuned on yours.
