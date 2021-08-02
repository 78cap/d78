"""implements a reverse merge
"""
from mercurial.i18n import _
from mercurial import (
    bookmarks,
    error,
    registrar,
    commands as c,
    bookmarks as b,
    cmdutil,
    scmutil,
    extensions,
    commands,
    revsetlang,
)

cmdtable = {}
command = registrar.command(cmdtable)
templatekeyword = registrar.templatekeyword()
predicate = registrar.revsetpredicate(revsetlang.symbols)
configtable = {}
configitem = registrar.configitem(configtable)

configitem(b'merge', b'anyrev', False)

OPT_ANYREV = b'anyrev'

@command(b'rmerge', [
    (b'', b'abort', None, _(b'abort the ongoing merge')),
    (b'', b'behind', None, _(b'show changes missing in the current bookmark')),
    (b'', b'ahead', None, _(b'show changes only in the current bookmark')),
    ] + cmdutil.mergetoolopts + cmdutil.logopts,
    _(b'NAME'),
    helpcategory=command.CATEGORY_MISC,
)
def cmd_rmerge(ui, repo, node=None, **opts):
    """integrate your changes into a branch/bookmark.

if NAME is not given, use parent bookmark.
    """
    o_abort = opts.get('abort') or opts.get(b'abort')
    o_tool = opts.get('tool') or opts.get(b'tool')
    o_behind = _pop_opt(opts, b'behind')
    o_ahead = _pop_opt(opts, b'ahead')

    ctx = repo[None]

    ctx_hex = ctx.p1().hex()
    bm = repo._activebookmark
    if not bm:
        raise error.Abort(_(b'A bookmark needs to be active'))

    ask_first = False
    if not node:
        node = _parent_bookmark_existing(repo, bm, fail=True)
        ask_first = ui.interactive()

    if o_abort:
        if not ctx.p2():
            raise error.Abort(_(b'There is no merge in progress'))
        c.bookmark(ui, repo, bm, rev=ctx.p2().hex(), force=True)
        c.update(ui, repo, bm, clean=True)
        return

    if ctx.p2():
        raise error.Abort(_(b'A merge is already in progress'))

    c_ahead = repo.revs(b'only(%d, %s)', ctx.p1().rev(), node)
    c_behind = repo.revs(b'only(%s, %d)', node, ctx.p1().rev())
    if o_behind or o_ahead:
        if not (opts.get(b'template') or opts.get('template')):
            tpl = ui.config(b'templates', b'oneline')
            if tpl:
                opts[b'template'] = b'oneline'
        if o_behind and c_behind:
            c.log(ui, repo, rev=c_behind, **opts)
        if o_ahead and c_ahead:
            c.log(ui, repo, rev=c_ahead, **opts)
        return

    # now the actual merge
    if ctx.files():
        raise error.Abort(_(b'Cannot merge with pending changes'))
    if not c_behind:
        ui.status(_(b'no new changes in %s\n') % node)
        return
    if not c_ahead:
        c.bookmark(ui, repo, bm, rev=node)
        c.update(ui, repo, bm)
        return

    done = False
    r = ui.prompt(_(b'Merge %s into %s? (y/n): ') % (node, bm), default=b'n') if ask_first else b'y'
    if r == b'y':
        try:
            c.update(ui, repo, node)
            c.merge(ui, repo, ctx_hex, tool=(o_tool or b':fail'))
            c.bookmark(ui, repo, bm, force=True, rev=b'.')
            b.activate(repo, bm)
            done = True
        finally:
            if not done:
                #c.bookmark(ui, repo, bm, rev=ctx_hex, force=True)
                c.update(ui, repo, node=ctx_hex)
            c_ctx = scmutil.revsingle(repo, bm)
            if c_ctx != c_ctx.p1():
                ui.status(_(b'bookmark %s moved from %s\n' % (bm, ctx_hex)))


def _parent_bookmark(bm):
    p = bm.rfind(b'/')
    return bm[0:p] if p > 0 else b'@'


def cmd_commit(orig, ui, repo, *pats, **opts):
    r = orig(ui, repo, *pats, **opts)
    activebookmark = repo._activebookmark
    if activebookmark:
        parent_bookmark = _parent_bookmark_existing(repo, activebookmark)
        if parent_bookmark:
            r_behind = _revset_only(repo, parent_bookmark, activebookmark)
            r_ahead = _revset_only(repo, activebookmark, parent_bookmark)
            ui.status(_(b'bookmark %s is now %d revisions behind, and %d ahead of %s\n') % (activebookmark, len(r_behind), len(r_ahead), parent_bookmark))
    return r

def cmd_merge(orig, ui, repo, node=None, **opts):
    anyway = _pop_opt(opts, OPT_ANYREV)
    o_preview = opts.get(b'preview') or opts.get('preview')
    o_abort = opts.get(b'abort') or opts.get('abort')
    if not anyway and not o_preview and not o_abort:
        activebookmark = repo._activebookmark
        if activebookmark:
            if not node:
                node = opts.get(b'rev') or opts.get('rev')
            if node and _parent_bookmark_existing(repo, activebookmark) != node \
                    and _parent_bookmark_existing(repo, node) != activebookmark \
                    and node + b'@default' != activebookmark \
                    and node != activebookmark + b'@default':
                raise error.Abort(_(b'Merging %s and %s is discouraged, add --%s if you really have to') % (activebookmark, node, OPT_ANYREV))
    r = orig(ui, repo, node, **opts)
    return r


def bookmarks_addbookmarks(orig, repo, tr, names, rev=None, force=False, inactive=False):
    orig_bm = set(repo._bookmarks.keys())
    r = orig(repo, tr, names, rev, force, inactive)
    if not rev:
        for name in names:
            if name != b'@' and name not in orig_bm:
                repo.ui.status(_(b'bookmark %s will be merged to %s when work is finished.\nrun hg rmerge periodically to get the latest from there.\n') % (name, _parent_bookmark_existing(repo, name)))
    return r


def _revset_only(repo, bm1, bm2):
    return repo.revs(b'only(%s, %s)', bm1, bm2)


def _revset_ancestor(repo, bm1, bm2):
    return repo.revs(b'ancestor(%s, %s)', bm1, bm2)


def _parent_bookmark_existing(repo, bookmark, fail=False):
    bookmarks = repo._bookmarks
    pbook = _parent_bookmark(bookmark)
    while pbook not in bookmarks:
        if pbook == b'@':  # there is no @ in the repo
            if fail:
                raise error.Abort(_(b'no parent bookmark found for %s') % bookmark)
            return None
        pbook = _parent_bookmark(pbook)
    return pbook


def _get_bookmark_from_ctx(context, mapping):
    ctx = context.resource(mapping, b'ctx')
    repo = context.resource(mapping, b'repo')
    bookmarks = ctx.bookmarks()
    if not bookmarks:
        return None
    bookmark = bookmarks[0]
    return repo, bookmark, _parent_bookmark_existing(repo, bookmark)

def _pop_opt(opts, name):
    if name in opts:
        return opts.pop(name)
    name = name.decode()
    if name in opts:
        return opts.pop(name)
    return None


@templatekeyword(b'revs_behind', requires={b'repo', b'ctx'})
def kw_revs_behind(context, mapping):
    """Integer. The number of changesets the bookmark is behind the parent."""
    repo, bookmark, parent_bm = _get_bookmark_from_ctx(context, mapping)
    return len(_revset_only(repo, parent_bm, bookmark)) if bookmark and parent_bm else None


@templatekeyword(b'revs_ahead', requires={b'repo', b'ctx'})
def kw_revs_ahead(context, mapping):
    """Integer. The number of changesets the bookmark is ahead of the parent."""
    repo, bookmark, parent_bm = _get_bookmark_from_ctx(context, mapping)
    return len(_revset_only(repo, bookmark, parent_bm)) if bookmark and parent_bm else None


@predicate(b'revs_ahead(name)', safe=True)
def p_ahead(repo, subset, x):
    """Changesets the bookmark is behind the parent."""
    name = revsetlang.getstring(x, _(b"revs_ahead requires a name"))
    return _revset_only(repo, name, _parent_bookmark_existing(repo, name, True))


@predicate(b'revs_behind(name)', safe=True)
def p_behind(repo, subset, x):
    """Changesets the bookmark is behind the parent."""
    name = revsetlang.getstring(x, _(b"revs_behind requires a name"))
    return _revset_only(repo, _parent_bookmark_existing(repo, name, True), name)


def reposetup(ui, repo):
    extensions.wrapfunction(bookmarks, 'addbookmarks', bookmarks_addbookmarks)


def uisetup(ui):
    extensions.wrapcommand(commands.table, b'commit', cmd_commit)
    if not ui.configbool(b'merge', b'anyrev'):
        entry = extensions.wrapcommand(commands.table, b'merge', cmd_merge)
        entry[1].append((b'', OPT_ANYREV, False, _(b'do not validate merge source')))
