# Wix Template for Bazel repository

This is just a template repository with vanialla bazel preparation.
 
 ## VERY IMPORTANT DISCLAIMER: 
 
 We prefer not to add new git repositories into the Virtual Mono Repository just like that. You are free to use this template if you want to play with bazel **locally** but if you want CI services on that repo - pleaes come to us first and consult.

## How to generate a new repository from this template?

1. Genenerate a new repostiry from this one
2. Edit `WORKSPACE` file first line `repository_name = "template_dont_use"`. The reposistory name should be the same as the new git repo name (change any `-` or `.` into `_`).
3. Change this README! 😁
4. Delete `sample-code`
5. Add your own code

That's it... now you can build **locally**

## What if I also want CI services?

### CI services include:
- CI builds on every push
- Labeldex indexing of current symbols
- Automatic deployables discovery and publishing
- Occusional batch updates of base bazel codebase (tools / WORKSPACE) in order to be aligned with what bazel infrastrcutrue needs.

Please contact us at `#bazel-support`.

