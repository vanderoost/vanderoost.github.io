---
date: 2026-11-13T12:00:00
authors:
  - richard
description: Setting up a brand new Mac from scratch with a single bash one-liner. Homebrew, SSH keys, GitHub, preferences, the Dock and dotfiles, all automated.
slug: automated-macos-setup-bash-script
categories:
  - Automation
  - Tutorials
tags:
  - macOS
  - Bash
links:
  - bootstrap on GitHub: https://github.com/vanderoost/bootstrap
  - dotfiles on GitHub: https://github.com/vanderoost/dotfiles
---

# Setting up macOS with a bash one-liner

![Automated macOS setup with a bash script](youtube:tf2lXmezrBA)

In this article we're automating the entire setup of macOS with a bash bootstrap script.

<!-- more -->

I'm not a big fan of upgrading my macOS the moment a new version drops. It feels like a
one-way door, and if something breaks it's kind of a pain in the neck. I'd rather keep
an old, stable setup and wait for the teething problems to be ironed out.

So up until last week I had been rolling a 3-year-old macOS 14 (Sonoma). But at last,
apps started complaining that my macOS was too old for the next update. So I figured
this is the moment I have to finally get with the times.

The most recent macOS as of writing this is macOS 27 (Golden Gate). That means I'm
skipping two versions: macOS 15 (Sequoia) and 26 (Tahoe).

With such a big leap, I thought it would be good to start fresh. So besides upgrading, I
also did a factory reset to set it up like it came straight out of the Apple Store.

To streamline this process, I've been using a bootstrap script that attempts to automate
as much as possible.

The script starts with a bash one-liner from my
[bootstrap repo](https://github.com/vanderoost/bootstrap). It:

*   Installs all my command line tools and apps with Homebrew
*   Creates an SSH key and connects it to GitHub
*   Sets all my macOS preferences, down to the apps in my Dock
*   Links my dotfiles, so Ghostty, Neovim and tmux look and behave like I'm used to

It doesn't only save me time. It also makes every Mac I set up exactly the same, which
is nice.

There are a few moments during the bootstrap script run where I have to step in:
clicking "Allow" on some permission popups, or logging in to something like Dropbox. But
for most of the run I can just go make a coffee.

Let's walk through the script and see what happens when you run it on a fresh Mac.

## The one-liner

After the factory reset, you do the usual stuff: Create an account, setup the
fingerprints etc. Then you land on a brand new desktop with all the default settings.

Now the bash one-liner: The script lives on GitHub, but this Mac has nothing on it. No
git repos, no SSH keys, no Homebrew. So the one-liner has to work with whatever a fresh
macOS comes with out of the box: `bash` and `curl`:

```console
$ /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/vanderoost/bootstrap/main/install.sh)"
```

`curl` downloads `install.sh`, and `bash -c` runs it. That's it. The Homebrew installer
for example does the same trick.

Only that one file is downloaded at this point. Later on, the script pulls in all files
of the bootstrap repo.

The first thing it does is ask for a hostname, with the current one as the default:

```console
==> STARTING MAC BOOTSTRAP SCRIPT
This script will set up command line tools, ssh, git, install all Homebrew
packages from the Brewfile, set up the Mac preferences and App preferences.
Enter this Mac's hostname [Richard’s MacBook Pro]: mb-pro
Your password is required for some admin work
Password:
```

And then it asks for my password. That should be the last time.

## Asking for the password only once

A lot of steps need `sudo`: installing updates, setting the hostname, and Homebrew asks
for your password all the time when it installs apps. This can get quite annoying, so I
wanted the script to ask for my password once, at the start, and then never bother me
again.

`sudo -v` refreshes your sudo timestamp, but that expires after a few minutes. And some
installers reset it. The only robust way I found was using a **sudoers file**.

Files in `/etc/sudoers.d` get read by `sudo` as extra rules. So the script writes a
temporary one that says "this user doesn't need a password":

```bash
SUDOERS_FILE="/etc/sudoers.d/bootstrap-nopasswd"

install_passwordless_sudo() {
    local tmp
    tmp="$(mktemp)"
    printf '%s ALL=(ALL) NOPASSWD: ALL\n' "$(id -un)" > "$tmp"

    if ! visudo -c -q -f "$tmp"; then
        rm -f "$tmp"
        abort "Refusing to install an unparseable sudoers rule"
    fi

    SUDOERS_INSTALLED="yes"
    sudo install -m 0440 -o root -g wheel "$tmp" "$SUDOERS_FILE"
    rm -f "$tmp"
}
```

I named it `bootstrap-nopasswd`, so if you ever find it lying around, you know where it
came from.

The rule is written to a temp file first, and checked with `visudo -c` before it's
installed. A broken sudoers file can lock you out of `sudo` entirely, so we'll proceed
with caution here!

Of course, the YOLO approach of "never ask for a password" is not a rule you want to
keep. So it has to be removed when the script is done (or exits for any reason).

That's what `trap` is doing here:

```bash hl_lines="11-12"
release_privileges() {
    if [ -n "$SUDOERS_INSTALLED" ]; then
        SUDOERS_INSTALLED=""
        sudo -n rm -f "$SUDOERS_FILE" 2> /dev/null \
            || echo "WARNING: please remove $SUDOERS_FILE by hand" >&2
    fi
    [ -n "$SUDO_KEEPALIVE_PID" ] && kill "$SUDO_KEEPALIVE_PID" 2> /dev/null
    [ -n "$CAFFEINATE_PID" ] && kill "$CAFFEINATE_PID" 2> /dev/null
    return 0
}
trap release_privileges EXIT
trap 'exit 1' INT TERM
```

`trap release_privileges EXIT` runs the function whenever the script exits, for any
reason. The second trap turns Ctrl+C (`INT`) into a normal `exit`, so the `EXIT` trap
fires there too.

Right after installing the rule, the script checks that it actually works. `sudo -k`
throws away the cached password, and `sudo -n` never prompts. It fails if a password
would be needed:

```bash
sudo -k
if ! sudo -n true 2> /dev/null; then
    echo "WARNING: /etc/sudoers.d is not read, expect password prompts" >&2
    sudo rm -f "$SUDOERS_FILE"
    SUDOERS_INSTALLED=""
    sudo -v
fi
```

If `sudo -n true` fails, the rule isn't being picked up, and we fall back to the regular
password prompts.

As a backup, a small loop runs in the background and refreshes the sudo timestamp every
30 seconds, for as long as the script is running:

```bash
(
    trap - EXIT INT TERM
    set +e
    while kill -0 "$$" 2> /dev/null; do
        sudo -n -v 2> /dev/null
        sleep 30
    done
) &
SUDO_KEEPALIVE_PID=$!
```

`kill -0` doesn't actually kill anything. It only checks if the process still exists. So
once the script exits, the loop stops by itself. That's the `SUDO_KEEPALIVE_PID` the
cleanup function kills, just in case.

## Staying awake

The whole run takes a while. I don't want the Mac to fall asleep halfway through because
I went to get coffee.

macOS comes with a command line tool for exactly this, and it has the best name:

```bash
caffeinate -dims -w "$$" &
CAFFEINATE_PID=$!
```

The flags prevent the display (`d`), the system when idle (`i`), the disk (`m`) and the
system on AC power (`s`) from sleeping. `-w "$$"` makes it wait for our script's process
ID (`$$`), and stop by itself once the script is done. It stays caffeinated :)

The `&` runs it in the background, and `$!` gives us its process ID, so the cleanup
function can kill it as well.

## All good

From here, most of the script follows the same pattern. Check if something is already
done. If it isn't, do it. If it is, say "All good" and move on:

```bash
green_echo "CHECK HOMEBREW STATUS"
if [ ! -x /opt/homebrew/bin/brew ]; then
    echo "Installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c \
        "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "All good"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"
```

`green_echo` is a small helper function that prints a header in green, so it's easy to
see where we are in the output:

```bash
GREEN='\033[0;32m'
NC='\033[0m' # No Color
green_echo()(echo; echo -e "==> ${GREEN}$1${NC}")
```

The same goes for the GitHub CLI (`command -v gh` tells us if it exists), the SSH key,
the repos, and so on. We don't create a new SSH key pair every time the script runs. If
it's there, we just move on.

This makes the script _idempotent_: you can run it as often as you want, and it only
does what still needs doing. That turns out to be really useful. If something fails
halfway, I fix it and run the whole thing again. And when I add a new app to the
Brewfile, I can just re-run the script and it stays up to date.

## SSH keys without copy-pasting

To clone my private repos, this Mac needs an SSH key that GitHub knows about. Creating
the key is just an `ssh-keygen` one-liner:

```bash
ssh-keygen -t ed25519 -f "$SSH_KEY_FILE" -q -N "" -C "$USER@$HOSTNAME"
```

`-N ""` skips the passphrase, so the script doesn't have to stop and ask for one.

The next step is usually opening `~/.ssh/id_ed25519.pub`, copying it, going to GitHub
settings and pasting it in there.

The best way I found to automate this is the [GitHub CLI](https://cli.github.com/),
which can upload keys for us. But it has to be logged in first, and that's one of the
few manual steps:

```bash
gh auth login --hostname github.com --git-protocol ssh --web \
    --skip-ssh-key --scopes "$GH_KEY_SCOPES"
```

`--web` gives you a one-time code, copies it to your clipboard, and opens the browser.
You log in, paste the code, click "Authorize", and the script moves on.

The `--scopes` are `admin:public_key` and `admin:ssh_signing_key`. Those are the
permissions `gh` needs to manage SSH keys. By asking for them at login, a fresh Mac only
needs one login to add the keys.

Then we upload the public key, twice:

```bash
add_github_key authentication
add_github_key signing
```

Once to authenticate (for `git clone` and `git push`), and once as a signing key. The
key title is the hostname I picked at the start, so on GitHub I can see which key
belongs to which Mac.

For the signing key to be useful, git has to actually sign with it. So the script also
configures that:

```bash
git config --global gpg.format ssh
git config --global user.signingkey "$SSH_KEY_FILE.pub"
git config --global commit.gpgsign true
```

Now every commit is signed with the same SSH key, and shows up as "Verified" on GitHub.

Being able to add SSH keys to my account is a big boy privilege. I don't need my
everyday `gh` token to have this kind of clearance. So once the keys are uploaded, the
script hands those scopes back:

```bash
# Key management is a privilege escalation, keep it off the daily token
echo "Dropping the key-management scopes again"
gh auth refresh --hostname github.com --remove-scopes "$GH_KEY_SCOPES"
```

That's a second trip through the browser, but I'd rather click "Authorize" one more time
than keep an over-powered token around.

Finally, it checks that SSH access works by connecting to `git@github.com`. GitHub
doesn't give you a shell there, but it does reply with a "successfully authenticated"
message. It's the standard way to test your SSH setup.

## The script downloads itself

The one-liner we kicked off with only downloaded `install.sh`. Now that we have GitHub
SSH access, the script can clone its own repo:

```bash
git clone "git@github.com:$GITHUB_USERNAME/$BOOTSTRAP_REPO_NAME"
```

That gives us all the other files the script needs: the Brewfile, the preferences
script, the Dock items, and so on. And on a re-run, the repo is already there, so it
just does a `git pull`.

## The Brewfile

Every app and command line tool I use is listed in a single Brewfile:

```ruby title="Brewfile"
brew "entr"
brew "fzf"
brew "gh"
brew "jq"
brew "neovim"
brew "rg"
brew "tmux"
...

cask "blender"
cask "dropbox"
cask "firefox"
cask "ghostty"
cask "rectangle"
...

mas "Bitwarden", id: 1352778147
mas "Xcode", id: 497799835
...
```

`brew` is for command line tools, `cask` for regular Mac apps, and `mas` for apps from
the App Store. Installing all of it is done in one line:

```bash
brew bundle --no-upgrade --file "$BOOTSTRAP_DIR/Brewfile"
```

This is the part that takes the longest. Every new app that needs special permissions
pops up a dialog, so you have to click "Allow" a bunch of times.

A few details around it:

*   `mas` can't sign in to the App Store by itself anymore. So if there are App Store
    apps left to install, the script opens the App Store and waits for me to sign in.
*   If one entry fails to install, I don't want the whole bootstrap to stop. The script
    remembers the failure and prints a warning at the very end instead.
*   `brew pin neovim` stops Neovim from being upgraded along with everything else. A new
    Neovim version breaking my config in the middle of the week is not my idea of fun.

## Preferences with `defaults`

The other big part is setting all my preferences. This is done with a second script that
is called by `install.sh`: `preferences.sh`.

Almost all of it uses the `defaults` command. The best way to think of it is as a
settings database for macOS. You can write to it, and you can also read from it.

For example the trackpad speed. On a fresh Mac, nothing has been set yet:

```console
$ defaults read -g com.apple.trackpad.scaling
The domain/default pair of (kCFPreferencesAnyApplication, com.apple.trackpad.scaling) does not exist
```

When a value isn't in the database, macOS falls back to the default. But if we drag the
"Tracking speed" slider in System Settings all the way to the fastest setting, we can
read the value:

```console
$ defaults read -g com.apple.trackpad.scaling
3
```

So 3 is the highest value the UI lets you pick. But nobody is stopping us from writing a
higher one ourselves:

```bash
# Increase trackpad speed (0.0 - 3.0 is the normal range)
defaults write -globalDomain com.apple.trackpad.scaling -float 5.0
```

That's another benefit of setting up preferences from the terminal: you can go beyond
the standard scale.

`-g`, `-globalDomain` and `NSGlobalDomain` all mean the same thing: the global domain
with settings that apply to every app. You'll come across all three flavours in the wild.

The rest of `preferences.sh` is a long list of things like this:

```bash
# Set a blazingly fast keyboard repeat rate
defaults write NSGlobalDomain InitialKeyRepeat -int 10
defaults write NSGlobalDomain KeyRepeat -int 1

# Don't use smart quotes
defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false

# Disable auto-correct
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# Show all file extensions
defaults write NSGlobalDomain AppleShowAllExtensions -bool true

# Save screenshots to Downloads to keep the Desktop clean
defaults write com.apple.screencapture location -string "$HOME/Downloads"
```

Finding the right key for a setting can be a bit of a pain. A trick that works well:
`defaults read` a domain, change the setting in System Settings, read it again, and see
what changed. I've used `diff` for this which worked quite nicely. Or just ask an LLM,
it's easy enough to verify.

Some changes only show up after the app restarts, so the script ends with:

```bash
for app in Finder SystemUIServer WindowManager; do
    killall "$app" 2> /dev/null || true
done
```

### Remapping keys

One thing `defaults` can't do is remap keys. For that, macOS has `hidutil`. I swap a
couple of keys around:

*   Caps Lock becomes Control
*   Left Control becomes Escape

The catch is that a `hidutil` mapping is gone after a restart. So the script installs it
as a launch agent, a little plist in `~/Library/LaunchAgents` that macOS runs at every
login:

```xml title="com.local.KeyRemapping.plist"
<key>ProgramArguments</key>
<array>
    <string>/usr/bin/hidutil</string>
    <string>property</string>
    <string>--set</string>
    <string>{"UserKeyMapping":[
        {
          "HIDKeyboardModifierMappingSrc": 0x700000039,
          "HIDKeyboardModifierMappingDst": 0x7000000E0
        },
        {
          "HIDKeyboardModifierMappingSrc": 0x7000000E0,
          "HIDKeyboardModifierMappingDst": 0x700000029
        }
    ]}</string>
</array>
<key>RunAtLoad</key>
<true/>
```

The hex values are so called *USB HID usage IDs*. The `0x7000000` prefix is the keyboard
page, and the last two digits are the key: `0x39` is Caps Lock, `0xE0` is Left Control
and `0x29` is Escape.

I've been using this for a couple of years now and it's pretty robust. It also applies
to external keyboards so you don't have to worry about doing this for every keyboard you
want to use.

## The Dock

This is a cool party trick. When this part runs, you can see the Dock icons changing live.

The apps I want in the Dock are listed in a plain text file, in order:

```text title="dock-items.txt"
/Applications/Ghostty.app
/Applications/Firefox.app
/System/Applications/Messages.app
/System/Applications/Mail.app
/System/Applications/Calendar.app
/System/Applications/Reminders.app
/System/Applications/Notes.app
/System/Applications/Podcasts.app
/Applications/Blender.app
```

And `dock-setup.sh` turns that into Dock tiles. It starts with a full reset (deleting
everything):

```bash
defaults delete com.apple.dock
killall Dock
```

(This doesn't break the Dock, it just makes it fall back to the default Dock settings
and icons.)

Then it builds one `<dict>` per app, and writes them all at once:

```bash
tiles=()
while read -r dock_item; do
    tiles+=("<dict><key>tile-data</key><dict><key>file-data</key><dict><key>_CFURLString</key><string>$dock_item</string><key>_CFURLStringType</key><integer>0</integer></dict></dict></dict>")
done < dock-items.txt
defaults write com.apple.dock "persistent-apps" -array "${tiles[@]}"
```

Those XML snippets are what the Dock stores for each tile. The array keeps app names
with spaces in one piece.

After that come a few Dock preferences: auto-hide, a shorter animation, and no
rearranging my desktops based on recent use.

## Apps on their own desktop

I like some apps to always go on the same desktop. That's configured in another text
file:

```text title="spaces-items.txt"
1 com.mitchellh.ghostty
2 org.mozilla.firefox
3 com.apple.mail
3 com.apple.Notes
4 org.blenderfoundation.blender
4 com.figma.Desktop
```

The script can bind apps to desktops, but I haven't found a good way to _create_
desktops from a script. So when there aren't enough, it prints this and waits:

```console
==> ASSIGN APPS TO DESKTOPS
Found 1 Desktops, but 4 are needed
Make sure you have enough Desktops, then press enter...
```

I open Mission Control, click the `+` three times, press enter, and it continues.

## Waiting for the human

Some steps can only be done by me: logging in to Dropbox, giving an app permission. For
those, the script opens the right window and waits.

Dropbox is the longest one. I keep a lot of my documents in Dropbox, and for example
link subfolders of `~/Documents` to it with symbolic links. Those links only make sense
once Dropbox is signed in and the folders exist. So the script checks for that every 5
seconds:

```bash
open -a Dropbox
echo "Waiting for the Dropbox sign-in (press enter to skip)"
until dropbox_ready; do
    if read -r -t 5 _ < /dev/tty; then
        echo "Skipping, Dropbox folders won't be linked"
        break
    fi
done
```

`read -t 5` waits up to 5 seconds for me to press enter. If I don't, it times out, and
the loop checks `dropbox_ready` again. So it's a polling loop, but I can skip it if I want.

On this Mac, Dropbox took ages to index before it synced the first folder. But I didn't
have to do anything. I went and did some work on my other laptop, and the script just
picked up where it left off as soon as the folders showed up.

The same idea sets up my Mail accounts. The bootstrap repo is public, so the email
addresses and passwords can't be in there. Instead, `mail-setup.sh` reads them from a
folder in my Bitwarden vault and generates a configuration profile. macOS doesn't let
scripts install profiles anymore, so it opens System Settings and waits for me to
approve it.

## Dotfiles

Then the dotfiles. The script clones my `home` and
[`dotfiles`](https://github.com/vanderoost/dotfiles) repos into `~/git`, and runs the
installer in `home`, which symlinks everything into place. The `home` repo has some
private settings, so I keep that one private.

This is the moment the Mac starts to feel like home. I open Ghostty, and it looks like
my terminal. No title bar, my font, my colours. Neovim and tmux are configured too.

## Switching apps with skhd

One last thing the script sets up: [skhd](https://github.com/asmvik/skhd), a hotkey
daemon. I use it to jump between apps without Cmd+Tab:

```text title="skhdrc"
rcmd - t : open /Applications/Ghostty.app
rcmd - w : open /Applications/Firefox.app
rcmd - e : open /System/Applications/Mail.app
rcmd - n : open /System/Applications/Notes.app
```

Right Cmd+T for the terminal, Right Cmd+W for the browser. I almost never use the right
Cmd key for anything else, so it's a free modifier.

---

That's how I automate my Mac setup. One command, and then mostly waiting. Sometimes I
have to jump in and click "Allow" or log in to something, but the rest of the time I can
do something else.

If you want to do this for your own Mac, don't run my script as is. You'd end up with my
apps, my Dock and my name in your git config. Instead, fork the
[bootstrap repo](https://github.com/vanderoost/bootstrap) (or just steal ideas from it),
and change:

*   The settings at the top of `install.sh` (your GitHub username, name and email)
*   The Brewfile
*   `dock-items.txt` and `spaces-items.txt`
*   Whatever you like in `preferences.sh`

This was a necessary detour. Next week we're back to C, writing a neural network :)
