# CHANGELOG

<!-- version list -->

## Unreleased

### Chores

- Stop tracking .idea/workspace.xml
  ([`2dfad7e`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2dfad7eb479d20b7d0d4878477feef19faa8d980))

### Continuous Integration

- Add GitHub Actions workflow for tests and syntax check
  ([`2be4e6a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2be4e6a019d6463db167fc9c482676f5b8cfad0c))

- Automate releases with python-semantic-release
  ([`4d58b80`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/4d58b8095177426c5433cc404a01a026f877d6f4))

- Bump checkout and setup-python to Node 24 versions
  ([`be8fcd9`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/be8fcd96c7af3ded75de2efa290ac454f7e9a3cb))

### Documentation

- Add CHANGELOG.md backfilled from history [skip ci]
  ([`0c80905`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/0c809057c534f120da26434229060358562bf34f))

- Add CLAUDE.md, fix stale README, add credit links [skip ci]
  ([`085ce54`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/085ce54c0cc809553f3ed1403a1187b1c9e4b264))


## v1.0.0 (2026-06-27)

### Bug Fixes

- **engine**: Bridge tooth roots into a single closed gear outline
  ([`5c8da58`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/5c8da58310f91591b2d44c11da7fa55b13d392af))

- **engine**: Center pinion tip arc on the pitch circle
  ([`7d59558`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/7d5955845a74e341a8c460c359e442641bbe52d6))

- **engine**: Size root depth from mating tooth addendum + clearance
  ([`3192b20`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/3192b20afc0eb929d9fff4a1c3fa92d1911ee4c5))

- **fusion**: Disable auto tangent constraints (they distorted the sketch)
  ([`d6f4fbf`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d6f4fbf2e3e16f55423779d651b7f1b882dcb9d3))

- **fusion**: Mirror tip spline per fit point (curve symmetry was a no-op)
  ([`9e0ca14`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/9e0ca14360a4a0914d033df2b316781f829d97d9))

- **fusion**: Referenced pitch circle to construction + pinion concentricity
  ([`b5e26a1`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/b5e26a1f135805af1d4e19e415552bd6b4d4a425))

- **ui**: Dropdown for clearance mode, robust logging, load message, icons
  ([`5d2a60a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/5d2a60a01c8127a476c89d731cc2c339238c00b7))

### Chores

- **docs**: Remove outdated TODO.md file
  ([`f1d083b`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/f1d083bff7680f055dbaeb32e75c461a75b1468a))

- **ide**: Update project configuration and metadata files for Python 3.14 and IDE setup
  ([`07d51cb`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/07d51cbab048fb661384bb2db7ccaab964f8e4c3))

- **resources**: Add 16x16 and 32x32 icons for `generateGears` command
  ([`42ba324`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/42ba32471772525e6a8801909d550ef1198b8e06))

### Documentation

- Add repo README (credits Steve Peterson for the concept)
  ([`6fa07d2`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/6fa07d24d9728524e01c92cc97289c2f16228c23))

- Handover/context summary (geometry saga + next steps)
  ([`538edfb`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/538edfb949f11bfa85d4155d90bc0cd98dba28c3))

- Require step-by-step collaborative geometry rebuild (not autonomous)
  ([`871b70f`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/871b70fdebf582f612843f113b200358842e526e))

- Revise spec + plan for validated Peterson geometry
  ([`9c47138`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/9c47138765fd078396ed42152fd3a6002289f987))

- Rewrite HANDOVER for v1-complete state + follow-ons
  ([`8598982`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/8598982ec0d8deeaf877934c3cbe8a2fb1d54229))

### Features

- **engine**: 2d rotate and line-intersection helpers
  ([`e748e74`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e748e741998844a39ea4471fb9abb637462ba61a))

- **engine**: Array teeth and assemble GearPair
  ([`2817766`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2817766e963ee469351e26cec7da9febefc7c221))

- **engine**: Assemble one wheel tooth from mirrored tip + flanks
  ([`bbc7046`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/bbc7046b1850ed43ff3878208e65be6ef172a32b))

- **engine**: Conjugate wheel-tip envelope
  ([`4d08c91`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/4d08c91f68af8952e8a6d520c3cefc9507915fb2))

- **engine**: Gear inputs and derived geometry
  ([`3c9da84`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/3c9da84bd51c5b53a5b58f89c0c2381e28a465be))

- **engine**: Input validation
  ([`ed73653`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/ed73653bbdfbddcc91484f087ac65f4316e7c9bb))

- **engine**: Pinion tooth with constant-width flanks and rounded tip
  ([`2683ed6`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2683ed6d4d4f672176ad7fc1b2fdff848ba04cc1))

- **engine**: Validated Peterson conjugate geometry + interference guard
  ([`73fa01b`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/73fa01b03b1e01af5b885fd92fbd59e42b98e89b))

- **fusion**: Constrain pinion tooth shape (flanks + cap)
  ([`4e20c8e`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/4e20c8ecfc6bac0023238311b16b569fc18b386b))

- **fusion**: Constrain wheel tip - apex + fixed lower spline, mirror to upper
  ([`15647cb`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/15647cb80d4664ea6d5da51f66841ac98a6a144f))

- **fusion**: Constraints step 1 - diameter dims on the three circles
  ([`28c7eec`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/28c7eecae791cf4b2843a754b52f615579196545))

- **fusion**: Constraints step 2 - wheel centres + pinion mesh tangent
  ([`de8e8d6`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/de8e8d63b40d180feec9d8ae8ee8f55dd9c873e6))

- **fusion**: Constraints step 3 - flanks + wheel centerline
  ([`e769a25`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e769a2559fd966a980c851b3d41901b843520dad))

- **fusion**: Drop redundant center point; pinion center horizontal w/ wheel
  ([`6193465`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/6193465611f13bbbc5fd6efe548448dd8c8b76ac))

- **fusion**: Pin pinion phase with angular dimension to line of centers
  ([`6ada978`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/6ada97811712c0ef0d1287a9a9b001b6a42be7dc))

- **fusion**: Single tooth -> extrude (disk+tooth) -> circular pattern solid
  ([`e0c359d`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e0c359d70e1ea6d24793f754643c4ed32e390da5))

- **fusion**: Sketch builder with tangent-arc tips
  ([`ad35a33`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/ad35a3320208bf26622bf8a594bfd73578226e28))

- **fusion**: Tangent-constrain wheel-tip splines to the flank join
  ([`5235300`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/52353005d20f311474dea6f37caa9824d55425df))

- **fusion**: Wheel flanks symmetric about centerline (+ keep equal)
  ([`fccc104`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/fccc104b62454e5eb50a8ff4daed0f670f926725))

- **settings**: Pure dialog-settings serialization and length resolution
  ([`8cb967a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/8cb967af36e4664ba70747606b531d7e3566e414))

- **ui**: Derive feature width, expose tooth fraction (Tasks 12 & 15)
  ([`11f5be6`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/11f5be64699b4ee4a00354231a1813b0e7232216))

- **ui**: GenerateGears command, dialog, validation, and execute
  ([`ae14a44`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/ae14a4447508c7f76c3a9c8e3637630fb25429f8))

### Testing

- **engine**: Peterson 50/10 golden check and second ratio
  ([`bd8ecc4`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/bd8ecc48532c445f12fba59c024cbf236f3144d5))
