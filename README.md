# paceline-legal

Hosted marketing site + legal pages for the
[Paceline](https://github.com/DoronK/paceline) app, served via GitHub
Pages on the custom domain `pacelinerun.com` (see `CNAME`). Kept in a
separate public repo so the main app repo can stay private.

- **Site**: https://pacelinerun.com/
- **Privacy policy**: https://pacelinerun.com/privacy/

Source of truth for the privacy policy content lives in the main
`paceline` repo at `docs/privacy-policy.md` — update there first, then
mirror the change into `privacy/index.html` here and push. The two
aren't auto-synced.

## Custom domain DNS

GitHub Pages serves this repo at the apex domain via 4 `A` records
(pointed at GitHub's Pages IPs) plus this repo's `CNAME` file — see
GitHub's [custom domain
docs](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)
if the domain ever needs to move to a different registrar/DNS host.
