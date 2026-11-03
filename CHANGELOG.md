# Changelog

## 0.1.0 (2026-11-03)


### Features

* **core:** add decibel and linear unit types that only average linearly ([3fdd208](https://github.com/soheil-mp/shoalscope/commit/3fdd2080f6ec7594fe17825d883dd0077cfb45c5))
* **core:** add Echolevels levels and processing attributes for provenance ([e36bc71](https://github.com/soheil-mp/shoalscope/commit/e36bc71eda674527b65f2866333fd6cf24c8cd6e))
* **lake:** write NASC cells to an Iceberg table with PyIceberg ([05577a1](https://github.com/soheil-mp/shoalscope/commit/05577a1a23886785b6724e0a74efb8770ca8ddd7))
* **proc:** add MVBS and NASC per time cell ([c79eef5](https://github.com/soheil-mp/shoalscope/commit/c79eef50b9b50438b6fe14a4c5be2f31b18a7d6b))
* **proc:** compute calibrated Sv and commit each window to Icechunk ([84f22e6](https://github.com/soheil-mp/shoalscope/commit/84f22e639b80450112f71af3585a3a43646c5d39))
* **sim:** add a minimal EK80 simulator that echopype reads and calibrates ([d000a2f](https://github.com/soheil-mp/shoalscope/commit/d000a2f2ad8c950e5c8b1c052c4a8bf1e85a1046))
* sync roadmap items to GitHub milestones and issues ([2e6c995](https://github.com/soheil-mp/shoalscope/commit/2e6c9959b95d60eea3293cafd662b329ab7f78aa))


### Documentation

* add contributing guide, code of conduct, security policy and templates ([143d58b](https://github.com/soheil-mp/shoalscope/commit/143d58b6d9b6815528bdb9ff69cc838121d80e6c))
* add contributor and assistant working rules ([16b9e54](https://github.com/soheil-mp/shoalscope/commit/16b9e54bc16eba21cd54b7d99e8191a9182b5b93))
* add README with purpose, audience, data, stack and setup ([1144ac2](https://github.com/soheil-mp/shoalscope/commit/1144ac2c09d6c98600da164480f9131cc47a4ea9))
* add roadmap with 26 milestones and 911 estimated hours ([a928f59](https://github.com/soheil-mp/shoalscope/commit/a928f598c7a20392c86d80e2dc13c4bf5357c00e))
* add target architecture with context, data-flow, edge and storage views ([570a90d](https://github.com/soheil-mp/shoalscope/commit/570a90d101208051f15902483d6932f6a5e54921))
* **adr:** record the first fourteen architecture decisions ([0e80db1](https://github.com/soheil-mp/shoalscope/commit/0e80db172749f33f53740b3ef235b6e429a5b76b))
* **examples:** add a byte-range example that reads one ping of a remote raw file ([d7795f0](https://github.com/soheil-mp/shoalscope/commit/d7795f07b89cfedd8fd0a8e78ee965a1a7e06008))
* publish a Zensical documentation site to GitHub Pages ([96e8b91](https://github.com/soheil-mp/shoalscope/commit/96e8b917f28b142b701c0fd0844a710918b805a3))
* record which sources ship index files and plan index-less window search ([0dc0685](https://github.com/soheil-mp/shoalscope/commit/0dc0685b8af8db081c013a17d4b3dbaf8fdcd312))
* **research:** add domain research on fisheries acoustics ([8d97bbf](https://github.com/soheil-mp/shoalscope/commit/8d97bbfbe06da09c8203a89507ee4e702af59d80))
* **research:** add technology landscape and tool selection ([e48f654](https://github.com/soheil-mp/shoalscope/commit/e48f6544a49e8d9b7850a62d34232b9bf25f9644))
* **research:** document data sources verified against the live services ([6a5eabb](https://github.com/soheil-mp/shoalscope/commit/6a5eabbe6ae02ccd57275d41645fcb045f63dddb))


### Build system

* add a dependency licence and no-ML scope check ([6530686](https://github.com/soheil-mp/shoalscope/commit/6530686821622f8284a7b522eb2c3fac4f6c7e91))
* add just task runner and a devcontainer ([719b0bb](https://github.com/soheil-mp/shoalscope/commit/719b0bb211287d520896993b835cebfce2920894))
* configure Renovate for grouped, scheduled dependency updates ([d619fa5](https://github.com/soheil-mp/shoalscope/commit/d619fa565f700dc31de7254e1b382a13a8f24fb3))
* set up the uv workspace with nine packages and quality tooling ([88c562b](https://github.com/soheil-mp/shoalscope/commit/88c562bb5322d51f97b53aae1a4284b7e981eb3e))


### Continuous integration

* add GitHub Actions workflow for lint, types, tests, secrets and hooks ([abcd95e](https://github.com/soheil-mp/shoalscope/commit/abcd95e0ff5272c9cf8ad8e459caa31180d578d7))
* automate releases with release-please and add citation metadata ([f5a000c](https://github.com/soheil-mp/shoalscope/commit/f5a000cc834c48d6a1e3aa740b2d21dd7efcc8f8))
