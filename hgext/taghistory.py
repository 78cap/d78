"""implements tag history command
"""
from mercurial.i18n import _
from mercurial import (
    error,
    registrar,
    commands,
    revsetlang,
    tags,
    cmdutil
)
try:
    from mercurial.utils.dateutil import datestr
except ImportError: # hg <= 4.5
    from mercurial.util import datestr
import binascii

MY_NAME = 'taghistory'
symbols = revsetlang.symbols
cmdtable = {}
command = registrar.command(cmdtable)
predicate = registrar.revsetpredicate(symbols)
templatekeyword = registrar.templatekeyword()


def get_tag_history(ui, repo, name):
    cachetags = tags.findglobaltags(ui, repo)
    if name in cachetags:
        anode, ahist = cachetags.get(name)
        h = binascii.hexlify(anode)
        revs = [h]
        visited = {h}
        for n in ahist:
            h = binascii.hexlify(n)
            if h not in visited:
                visited.add(h)
                revs.append(h)
        return revs
    else:
        raise error.UnknownIdentifier(name, cachetags.keys())


@templatekeyword(b'ver78', requires={b'ctx'})
def kwver78(context, mapping):
    """String. The changeset as a version string."""
    ctx = context.resource(mapping, b'ctx')
    date_s = datestr(ctx.date(), '%y.%-m.%-d.%-H%M')
    while b'.0' in date_s:
        date_s = date_s.replace(b'.0', b'.')
    if date_s.endswith(b'.'):
        date_s += b'0'
    ver = date_s + b'+r' + ctx.hex()[:12]
    return ver


@command(b'taghistory',
    cmdutil.logopts,
    _(b'NAME'),
    helpcategory=command.CATEGORY_MISC,
)
def cmd_taghistory(ui, repo, name, **opts):
    """Get a tag history.

    Gets the list of commits that were ever tagged as <name>
    """
    if not opts.get(b'template'):
        tpl = ui.config(b'templates', b'oneline')
        if tpl:
            opts[b'template'] = tpl[1:-1].strip().replace(b'{ansi_node}', b'\033[0;33m{ver78}')
    commands.log(ui, repo, rev=get_tag_history(ui, repo, name), **opts)


@predicate(b'taghistory(name)', safe=True)
def p_taghistory(repo, subset, x):
    """Get a tag history.

    Gets the list of commits that were ever tagged as <name>
    """
    name = revsetlang.getstring(x, _(b"taghistory requires a name"))
    return get_tag_history(repo.ui, repo, name)
