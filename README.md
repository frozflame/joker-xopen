joker-xopen
===========

### `xopen` command (client)

Without any config, you can use `xopen` as a cross-platform version `xdg-open` (Linux), `open` (macOS) or 
`start` (Windows).

    $ xopen https://www.pypi.org 
    $ xopen ~/sample-video.mp4


Show help:

    $ xopen -h
    

-----------------------------------------------------------
 
### Server

Show help

    $ python3 -m joker.xopen.server -h
    
    
Put a text file at `~/.joker/xopen/xopen.txt`, with content like

    c   ~/Code
    w   /var/www/html
    ns  /etc/nginx/servers
    ff  https://github.com/frozflame
    
    
Run server:

    $ python3 -m joker.xopen.server 
    
    
Then try

    $ xopen c
    $ xopen ff
    

To save some typing, you can give `xopen` an alias. Add in `~/.bashrc` or `~/.zshrc`:

    alias xo=xopen
     
