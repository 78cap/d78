"""filters out files that were modified independently but are the same from the status command
"""
from mercurial.i18n import _
from mercurial import (
    patch as p,
    localrepo,
    extensions,
    commands
)

def _filter_status(ui, repo, node1, node2, status):
    ctx1 = repo[node1]
    ctx2 = repo[node2]

    # check if it's just a test for working directory status
    if node1 == node2 or (node2 is None and (ctx2.p1() == ctx1 or ctx2.p2() == ctx1)):
        ui.note(_(b'not using --effective when comparing %s and %s\n') % (ctx1, ctx2))
        return
    unchanged_files = {}
    for fctx1, fctx2, hdr, hunks in p.diffhunks(
        repo,
        ctx1=ctx1,
        ctx2=ctx2,
        # match=match,
        # changes=changes,
        # opts=opts,
        # losedatafn=losedatafn,
        # pathfn=pathfn,
        # copy=copy,
        # copysourcematch=copysourcematch,
    ):
        if fctx1 is not None and fctx2 is not None and len(hdr) <= 1 and not hunks:
            unchanged_files[fctx1.path()] = b''
    i = 0
    m = status.modified
    while i < len(m):
        if m[i] in unchanged_files:
            ui.note(_('= %s\n') % m[i])
            # status.clean.append(m[i])
            del m[i]
        else:
            i += 1

def commands_status(orig, ui, repo, *pats, **opts):
    # bypass if
    # - effective flag is off
    # - or paths are specified
    # - or base/target rev are not specified
    effective = opts.get('effective')
    revs = opts.get(b'rev') or opts.get('rev')
    if not effective or (pats and pats[0] != b'.') or not revs:
        if effective:
            ui.note(_(b'not using --effective rev=%s, paths=%s\n') % (revs, pats))
        return orig(ui, repo, *pats, **opts)

    orig_status = localrepo.localrepository.status
    def clean_status(zelf, *args, **kwargs):
        r = orig_status(zelf, *args, **kwargs)
        _filter_status(ui, zelf, args[0], args[1], r)
        return r
    try:
        localrepo.localrepository.status = clean_status
        return orig(ui, repo, *pats, **opts)
    finally:
        localrepo.localrepository.status = orig_status

def uisetup(ui):
    entry = extensions.wrapcommand(commands.table, b'status', commands_status)
    entry[1].append((b'', b'effective', True, _(b"hide changes that won't affect the target revision, like identically modified files")))
