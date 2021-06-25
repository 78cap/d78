"""implements a right-side merge
"""
from mercurial.i18n import _
from mercurial import (
    error,
    registrar,
    commands as c,
    bookmarks as b,
    cmdutil,
    scmutil,
)

cmdtable = {}
command = registrar.command(cmdtable)

@command(b'rmerge', [
    (b'', b'abort', None, _(b'abort the ongoing merge')),
    ] + cmdutil.mergetoolopts,
    _(b'NAME'),
    helpcategory=command.CATEGORY_MISC,
)
def cmd_rmerge(ui, repo, node=None, **opts):
    """integrate your changes into a branch/bookmark.
    """
    o_abort = opts.get('abort') or opts.get(b'abort')
    o_tool = opts.get('tool') or opts.get(b'tool')

    ctx = repo[None]

    ctx_hex = ctx.p1().hex()
    bm = repo._activebookmark
    if not bm:
        raise error.Abort(_(b'A bookmark needs to be active'))

    if not node:
        p = bm.rfind(b'/')
        node = bm[0:p] if p > 0 else b'@'

    if o_abort:
        if not ctx.p2():
            raise error.Abort(_(b'There is no merge in progress'))
        c.bookmark(ui, repo, bm, rev=ctx.p2().hex(), force=True)
        c.update(ui, repo, bm, clean=True)
        return
    if ctx.p2():
        raise error.Abort(_(b'A merge is already in progress'))

    if ctx.files():
        raise error.Abort(_(b'Cannot merge with pending changes'))
    c_ahead = repo.revs(b'only(%d, %s)', ctx.p1().rev(), node)
    c_behind = repo.revs(b'only(%s, %d)', node, ctx.p1().rev())
    if not c_behind:
        ui.status(_(b'no new changes in %s\n') % node)
        return
    if not c_ahead:
        c.bookmark(ui, repo, bm, rev=node)
        c.update(ui, repo, bm)
        return

    done = False
    try:
        c.update(ui, repo, node)
        c.merge(ui, repo, ctx_hex, tool=(o_tool or b':fail'))
        c.bookmark(ui, repo, bm, force=True)
        b.activate(repo, bm)
        done = True
    finally:
        if not done:
            #c.bookmark(ui, repo, bm, rev=ctx_hex, force=True)
            c.update(ui, repo, node=ctx_hex)
        c_ctx = scmutil.revsingle(repo, bm)
        if c_ctx != c_ctx.p1():
            ui.status(_(b'bookmark %s moved from %s\n' % (bm, ctx_hex)))
