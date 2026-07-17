# CHANGELOG

<!-- version list -->

## v1.11.0 (2026-07-17)


## v1.10.0 (2026-07-16)

### Documentation

- Document optional end-gear bounds in the calculator
  ([`1e7df65`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/1e7df65bd7c3411344ad5f56cae8008af227f815))

### Features

- **engine**: Add optional end-gear tooth bounds to TrainQuery
  ([`da6f1e8`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/da6f1e8ab251c728a4b5aee9a1aa565a5fa88af5))

- **engine**: Filter and order trains by end-gear bounds at the leaf
  ([`45057ea`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/45057ea7527729fc3dc91bd201b49cdff5d3df5b))

- **fusion**: Add End gears fieldset to the calculator palette
  ([`f95867c`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/f95867c1ea1290c1d8727f50a75f1e08d25c2e98))

- **fusion**: Forward end-gear bounds from the palette to the engine
  ([`0313bc9`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/0313bc9f56d7749ed958858d9cdbeff3a765f92e))

- **fusion**: Wire end-gear checkboxes, validation, and query in the palette
  ([`c12d41e`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/c12d41ef319d9f8fa7c86e3256bd2ddc79ad7334))

### Testing

- **engine**: Cover bounded search ordering and brute-force parity
  ([`913c0ae`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/913c0aebe5172716f3695e3421b9e260360553f4))

- **engine**: Harden bounded gate and add coaxial+bounds parity test
  ([`2c37c4c`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2c37c4c1318541274716bed5df7af0fe376993e2))

- **engine**: Tighten end-gear bound validation tests and comment
  ([`70c2a95`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/70c2a95e0722953a0dca2fbd9444d01a656eb09a))


## v1.9.1 (2026-07-16)

### Bug Fixes

- **fusion**: Label gear-train calculator ratio as input : output
  ([`6f0ac92`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/6f0ac92a4c80b775a323e5ef14e7315f90f1c57a))


## v1.9.0 (2026-07-04)

### Bug Fixes

- **fusion**: Use forward slashes in palette htmlFileURL
  ([`86feaf1`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/86feaf1d3c70e4fbc9dde1935e7fad96577b8f7e))

### Documentation

- Add 21/45 gear pair DXF example
  ([`715d294`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/715d294b7acd08f7da7fb2000e3fee1ba7a208e2))

- Credit Steve Peterson and link his site in the add-in description
  ([`7b058fe`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/7b058fea69eb6f9582a2e2866fe8fbfb4d19635b))

- Document the gear-train calculator command
  ([`b7776da`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/b7776da51cddfdd42839ca3727b1d9f1aaf4ff8b))

- Document the Sizes readout and the calculator in the README overview
  ([`0246070`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/02460704076ca98d2ae03ea9e69326428cb6ac08))

### Features

- **engine**: Add gear-train data model (Stage, GearTrain)
  ([`1f32264`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/1f322644672bd5ec8c0eff4f0c086615301292f8))

- **engine**: Add TrainQuery and query validation
  ([`2f361d4`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2f361d471977542da1450d1f75c970de0ab7045d))

- **engine**: Coaxial equal-tooth-sum constraint
  ([`e577cf6`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e577cf616f8e7d65423fc09b2885fbbb6fb77031))

- **engine**: JSON serialization of search results
  ([`7d58986`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/7d58986d58a0c4273e178b919b202a17a8bfbb4f))

- **engine**: Normalize queries (coaxial min-stage bump, warnings)
  ([`a7be110`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a7be1107bbe6e37a338240519503a97252e9a1fa))

- **engine**: Pruned recursive search for exact n-stage trains
  ([`52c5975`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/52c59752b7d0b0d1f1263a96abcab8bcf239eca8))

- **engine**: Rotation-direction parity filter in search()
  ([`6af526e`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/6af526e3b3db55936c867d807f4965b7f9984f00))

- **engine**: Search() with dedup, ordering, and result cap
  ([`c4f37af`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/c4f37af26d4d163b5643a423b77cb04ee683bc25))

- **fusion**: Add gear-train calculator palette launcher
  ([`8d4e56f`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/8d4e56f943836dea45e0e1194d9d50cdfb79b430))

- **fusion**: Add search busy indicator; default rotation to same-as-input
  ([`a1b2342`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a1b23423714587e0647fc57f3423aaec66665112))

- **fusion**: Dedicated gear+table icon for the gear-train calculator
  ([`1a2facb`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/1a2facb7a489fee6ff689c555370842c353c54ba))

- **fusion**: Gear-train calculator palette UI (form + results table)
  ([`35f8550`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/35f8550a93b6abfb2c38414c2621c8ba21e5f964))

- **fusion**: Move gear-train calculator to Utilities > Add-Ins, pinned
  ([`fdf76e8`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/fdf76e86ee2aa60d24e63927ca045a45f3464cd9))

- **fusion**: Preview pitch diameters and center distance in the generator dialog
  ([`74df290`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/74df2906ee3dab20e828a368abebf08d5736149a))

- **fusion**: Register the gear-train calculator command
  ([`326fda5`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/326fda5da5772468c30e71b5a6bdd97ba8f33c03))

### Performance Improvements

- **engine**: Bound gear-train search (dedup, cap-aware loop, safety valves)
  ([`a9b94df`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a9b94dfb85610245a12d52ac4126ada758402ea1))

### Testing

- **engine**: Brute-force equivalence guard for pruned search
  ([`d364f8a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d364f8a4c2b8ab1d571beb2dc85458e29be2de7c))


## v1.8.0 (2026-06-29)

### Chores

- Add gear example step file [skip ci]
  ([`d04e8f1`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d04e8f1839c65887d690241c896612948aabc41b))

- Replace gear example step file with elliptical-tip 21/45 pair [skip ci]
  ([`7470f40`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/7470f4035f1229ea92ee19cbe5c9171124b513a1))

### Documentation

- Describe the elliptical driven tip in README and manifest
  ([`5a98dcb`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/5a98dcbf91e150db521b1e216f2423f118400669))

### Features

- **engine**: Add 'earc' elliptical-arc segment + densification
  ([`4008a33`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/4008a3307b124735909da940cb83921197d057a8))

- **engine**: Elliptical driven tip (Perfect Print blue), flanks end inside pitch circle
  ([`b0badda`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/b0badda138430aa8a6a5387df3fc4cce1a3d9692))

- **fusion**: Draw the driven tip as a native elliptical arc
  ([`442198a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/442198a6442fc931e7d9f93a6e163a17bb7ae759))

- **fusion**: Fully constrain the driven oval cap; draw it as a full ellipse
  ([`e8b9186`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e8b918620950c192d7fef7b847171e7fa5a6309a))

### Refactoring

- **engine**: Clarify earc contract + strengthen rotation test
  ([`3b82bb3`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/3b82bb32e908c14f3fc934951bb09d99483fde9f))

- **engine**: Decouple oval tip from the driving tooth
  ([`4586c63`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/4586c63835135c823a0cb5fe21aa0d5bebfa5dac))

### Testing

- **engine**: Regression guard that the oval tip beats the round tip at snug fit
  ([`d80d345`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d80d345d96b73065ce17501d4da8da393cf8121b))


## v1.7.0 (2026-06-28)

### Documentation

- Align CLAUDE.md with driving/driven terminology
  ([`bc01518`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/bc01518c222a8f4e5d104faa950e8cfc3e782004))

- Driving/driven terminology and reduction support
  ([`2e601d2`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2e601d2b063b7516646a9ba39f3c5c0e24696d54))

### Features

- **engine**: Allow reductions and 1:1; min teeth on both gears
  ([`fa4e41a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/fa4e41a689d14e8834426e5212c1729034484436))

- **engine**: Direction-aware ratio readout (step-up/reduction/1:1)
  ([`8e8d171`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/8e8d1715ba3f2c5f571144bcd4bf85d12434bf44))

- **fusion**: Name the face-derived helper plane with both tooth counts
  ([`ea323a6`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/ea323a63eb30d3fb6f0fc7665d4692e95ab0f498))

### Refactoring

- **engine**: Rename wheel/pinion -> driving/driven
  ([`d69d4bc`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d69d4bc62c77151c55ec41b577e3fe259a98fa65))

- **fusion**: Rename wheel/pinion -> driving/driven in UI and builder
  ([`1a0f30f`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/1a0f30fccb72aa27b5af7c8d91e3dfef64e8802d))

### Testing

- **engine**: Guard interference for reductions and 1:1
  ([`b031c46`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/b031c461e3c51974a63e340261314c79f6cb055e))


## v1.6.1 (2026-06-28)

### Bug Fixes

- Cut maintenance release for public launch
  ([`bf25fd2`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/bf25fd2bd7532ab9f8484bd55cd9ddd69b65c8dd))

### Chores

- Stop tracking .idea, add NOTICE for Autodesk template
  ([`08e4902`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/08e4902ba3b62d914249a7920d1a26bc26c3158f))

- Stop tracking docs folder
  ([`e430e7b`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e430e7bbeb5db78b00419c9e65a0f8f0659beb6a))

### Continuous Integration

- Release job pushes with RELEASE_TOKEN to satisfy ruleset
  ([`8c71529`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/8c71529eb756d6b1d7327cd199d28f7eb058a7f3))

### Documentation

- Drop docs/ reference, refresh scope, add Apache-2.0 footer
  ([`58cbc5e`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/58cbc5e09057dc48a3115d25a57e94d0f501ceb3))


## v1.6.0 (2026-06-27)

### Bug Fixes

- **fusion**: Suppress startup message box when auto-loading at launch
  ([`2d94a77`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2d94a77f507d3c849a254069e7e9f30d52724ec5))

### Chores

- Update .gitignore
  ([`24e12f8`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/24e12f801c073534b51a8fb15087b6e373fc1c9d))

- **fusion**: Do not promote the command to the panel
  ([`a02e76c`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a02e76c1e01562ef138e6a20cbf593834c1239bf))

- **fusion**: Quiet the Text Commands palette to errors only
  ([`f0b9445`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/f0b944596edd4504c7705e74e889929756fb7566))

### Documentation

- Mark editable tooth width done (PR #9)
  ([`f587e16`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/f587e1628cd06d100e926566b5f64257b6304478))

- Tooth width is now an editable, module-linked input
  ([`007d370`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/007d3704f3a14332d2053490367b6b67caecb1ec))

- **plan**: Editable, module-linked tooth width implementation plan
  ([`47b7799`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/47b7799e1918e1d688504c0fcd63ff66a10075b2))

- **spec**: Editable, module-linked tooth width design
  ([`8eaa985`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/8eaa985424c68c757ff756ef591a588b975bec7e))

### Features

- **engine**: Add tooth-width <-> module helpers
  ([`bf910e1`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/bf910e1e24098cb4303bcd346ea457dc60bab87b))

- **fusion**: Editable tooth width linked bidirectionally with module
  ([`f9638ba`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/f9638baf700458d95986a21424cd9f6070c5635f))

### Refactoring

- Remove inert addendum factor input
  ([`274f14f`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/274f14f3c86dee7183acb8cd120a6f02fff17483))

- **fusion**: Group module/tooth-fraction/tooth-width in a Tooth sizing group
  ([`fbffd97`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/fbffd973336d81cfa7d9743ff961fc09eeae5ffe))


## v1.5.0 (2026-06-27)

### Bug Fixes

- **fusion**: Anchor pinion line of centers to the wheel centre, not the origin
  ([`2026a33`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2026a33d443464f512e6902649d42caae7d9e31a))

### Documentation

- Add free-swing-pinion design spec
  ([`a870466`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a87046613f2b93f741f3ba70fb0dcd4ebf04c990))

### Features

- **fusion**: Leave the pinion free to swing for feature alignment
  ([`c4e080c`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/c4e080ca948a30adecdfd605e320303d7c0f7a64))


## v1.4.0 (2026-06-27)

### Documentation

- Document control-point tip, tangent toggle, and rotatable wheel
  ([`440f09a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/440f09a4325f046509fcf804fe9c56b273b9154d))

- Revise rotatable-wheel design to control-point spline + tangent toggle [skip ci]
  ([`7cfd480`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/7cfd4809d9ddb1bd4f2e92c5e4f4d4993dbc75c1))

- **plan**: Add rotatable wheel sketch implementation plan [skip ci]
  ([`af7fdac`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/af7fdac93f40f50d1f5a1d9207f684e070eef2fe))

- **spec**: Add rotatable wheel sketch design [skip ci]
  ([`a747f18`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a747f187490e2745f3cc062ac99a2270ac211087))

### Features

- **engine**: Add pure-python cubic/quintic Bezier fit for the wheel tip
  ([`e0db6b6`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e0db6b6269b30bf9cfb48014b399b80ac39243dd))

- **engine**: Persist the tangent_join tip toggle in settings
  ([`c2c90c2`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/c2c90c21c798084ef572f38cb7b8188352689929))

- **engine**: Represent wheel tip as a control-point Bezier (unifies drawn+validated)
  ([`09c2fe3`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/09c2fe3d5f0fa48f6f59e8d4f72dd682caec9510))

- **fusion**: Add tangent-tip-join toggle with a low-control-point warning
  ([`9de088b`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/9de088b989c53c74bcb976c069ddf5f857fca312))

- **fusion**: Draw the wheel tip as a constrained control-point spline
  ([`adfa7f2`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/adfa7f2c795f3b8d93efbc4c34c461bdfd0b19e5))

- **fusion**: Drive wheel orientation by an angle dimension (rotatable)
  ([`eb705a5`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/eb705a588cd6238a5154b1b5d94c9b7d84f73207))

### Refactoring

- **engine**: Remove dead cubic-spline tip machinery superseded by the Bezier
  ([`037168d`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/037168d188bb9281d9d4a55c21c9f5d664a9b639))


## v1.3.0 (2026-06-27)

### Features

- **fusion**: Name each gear body after its sketch
  ([`48992c0`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/48992c030ebf8235fb8715869cbd9a925789e194))


## v1.2.0 (2026-06-27)

### Continuous Integration

- Trigger checks for PR #5
  ([`d7dace5`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d7dace5f7f793f99154099f97204f69697cd22e7))

### Documentation

- Document the placement inputs (components, plane, center)
  ([`01a5381`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/01a5381e0d8b75c3d0ef75f29744668aac72e3bf))

- Update handover with placement & targeting features [skip ci]
  ([`9b4f6de`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/9b4f6de668295afd2c415efeedc5d194285bac4d))

- **plan**: Add placement & targeting implementation plan [skip ci]
  ([`a42bb7f`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/a42bb7f76188d3ba1f002322a124fbbc40631c8d))

- **spec**: Add placement & targeting design [skip ci]
  ([`9ff4a07`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/9ff4a07dcc673fa76713c13ae4582d62746b5c05))

### Features

- **fusion**: Build wheel and pinion into separate components
  ([`3c9d67c`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/3c9d67ce0d9f14c9492b2052399376b7440b2d02))

- **fusion**: Let the user pick the sketch plane for the gears
  ([`96b8d9b`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/96b8d9b90d1cfba181a4636db2b653c1c55c7b78))

- **fusion**: Let the user pick the wheel center point
  ([`0ccefae`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/0ccefaeff91dbeb58f398a6df59f418626ed193e))


## v1.1.0 (2026-06-27)

### Bug Fixes

- **fusion**: Drop redundant second tangent on pinion cap
  ([`1a89eb8`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/1a89eb8b037060a653b09eae7dca13f4bfc3ed44))

- **fusion**: Skip degenerate symmetry on wheel tip apex
  ([`6d2c423`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/6d2c4234ddb765ff79f2ece4474906dc3e46a566))

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

- Instruct agents to use Conventional Commits format [skip ci]
  ([`02e4005`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/02e400520da8f7fcef8010dc14ad1da0dd9b8de1))

- Itemize v1.0.0 commits in changelog [skip ci]
  ([`e20c7da`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e20c7da046f8b71be7a07070c9c23bd05d440d86))

- Note the gear ratio readout in the dialog
  ([`2b59a9f`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/2b59a9f001c855681351446307a5684b7f7790f7))

- Update handover with dialog readouts, 0.45 default, constraint fixes [skip ci]
  ([`63a590a`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/63a590a31c0e9227e38bc839edf1bc2625fb2190))

- **plan**: Add gear ratio readout implementation plan [skip ci]
  ([`16de4ec`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/16de4ecd10cead98a43e9c0707e753aa55907804))

- **spec**: Add gear ratio readout design [skip ci]
  ([`44fd895`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/44fd8955e64b1face0aa41c82a9619294ffb3577))

### Features

- **engine**: Add format_ratio helper for dialog ratio readout
  ([`d195c20`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/d195c20ee52afa0bbe9d5b5b9f957bb6b5c74ab7))

- **fusion**: Default tooth fraction to 0.45 for meshing backlash
  ([`8203946`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/82039469ff9f7c053401a6c629e4d3fed1433f29))

- **fusion**: Show live gear ratio readout in the generate dialog
  ([`4b165c7`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/4b165c712700a41213c5a2a05266bba71b9af954))

- **fusion**: Show tooth width as a read-only text field
  ([`e6a9c28`](https://github.com/LordRaptor/Fusion360PerfectPrintGears/commit/e6a9c286d61cfe49417e599259407bbdbd1bbad3))


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
