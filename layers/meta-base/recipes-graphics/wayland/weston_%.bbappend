# Fix RDEPENDS override from base.yml (pixman) being replaced by xkeyboard-config
# We need both xkeyboard-config AND pixman
RDEPENDS:${PN} += " pixman"