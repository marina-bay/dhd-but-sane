# Build process

**Name**: `hybris-run`/`hybris-helper`/`droid-helper`/...?

**Operations:**

- `help`/`usage`
- `droid-hal`
- `droid-configs`
- `droid-version`
- `middlewares`
- `droid`: all of droid-hal, droid-configs, middlewares, droid-version
- `create-image`
- `build-package`
- `sync-packages`: clone all middlewares and pull in all dependencies, but do not
  install yet(useful if you want to go `--offine` later)
- `setup-env`: install createrepo, android-tools, piggz etc
- `audioflingerglue` & `droidmedia`

**Options**:

- `--offline`: only refresh droid-local-repo, if any
   (packages already in
   /srv/mer/sdks/sfossdk/var/tmp/mic/cache/packages/)
- `--spec`
- `--url`
- `--revision`(`--branch` for compatibility)
- `--dir`: if explicitly skipping e.g. external/droidmedia
         in favour of hybris/mw/droidmedia

# Build stages:
Prerequisites(from util.sh):

- logging
- install:
  - createrepo
  - android-tools
  - android-tools-hadk
  - for sailfish x:
      - piggz
      - lvm2
      - atruncate
- set unsigned rpm
- make sure mesa-llvmpipe is not installed

## helpers

**build()**

- build supplied .spec files or build all found .spec files
- mb2 -s $SPEC -t $VENDOR-... build
- save built rpms to RPMS.saved in case of multiple .spec files
  (mb2 kills RPMS/ on invocation)

**process_patterns()**

- simply runs the script(or absorb the script into build system)
- hard dependency for nearly everything!!! (at least for mic)

**deploy()**

- mkdir/clean $ANDROID_ROOT/droid-local-repo/$DEVICE/$PKG
- copy saved rpms back
- add to repo with createrepo
- ssu addrepo $LOCAL_REPO
  (ssu is kinda like zypper but seems to manage credentials or sth)
- zypper refresh

## manual
- preserve current functionality with --spec, --mw,
  clone urls etc for one-off stuff
- clone with submodules
- process_patterns()

## droid-hal
- build `droid-hal-$DEVICE.spec`: check `droid-hal-device.inc` from d-h-d for
  all the particulars, it's a lot!
- deploy with do_not_install

## droid-config
- check for `community_adaptation` and install `community-adaptation`
  (`_` -> `-`!)
- if not available, build `community-adaptation-localbuild`
- inside sb2: `mkdir -p /system; echo ro.build.version.sdk=99 > /system/build.prop`
- build `droid-config-$DEVICE.spec`
- deploy with do_not_install
- extract patterns from `droid-config-$DEVICE-ssu-kickstarts-1-1.$PORT_ARCH.rpm`
- process_patterns()

...and all this bs for which there should really be a better way:
```
if [ -z "$(grep community_adaptation $ANDROID_ROOT/hybris/droid-configs/rpm/droid-config-$DEVICE.spec)" ]; then
  sed -i '/%include droid-configs-device/i%define community_adaptation 1\n' $ANDROID_ROOT/hybris/droid-configs/rpm/droid-config-$DEVICE.spec
fi
if [ -z "$(grep patterns-sailfish-consumer-generic $ANDROID_ROOT/hybris/droid-configs/patterns/jolla-configuration-$DEVICE.yaml)" ]; then
  sed -i "/Summary: Jolla Configuration $DEVICE/i- patterns-sailfish-consumer-generic\n- pattern:sailfish-porter-tools\n" $ANDROID_ROOT/hybris/droid-configs/patterns/jolla-configuration-$DEVICE.yaml
fi
if [ -z "$(grep jolla-devicelock-daemon-encsfa $ANDROID_ROOT/hybris/droid-configs/patterns/jolla-hw-adaptation-$HABUILD_DEVICE.yaml)" ]; then
  sed -i "s/sailfish-devicelock-fpd/jolla-devicelock-daemon-encsfa/" $ANDROID_ROOT/hybris/droid-configs/patterns/jolla-hw-adaptation-$HABUILD_DEVICE.yaml
fi
```

## middlewares
- clone in parallel
- update to a revision defined in yaml, pull latest
  or do nothing(if cloned through repo)
- check git dir:
  - if that revision is installed, skip(but warn!)
  - if tree is dirty, always rebuild
  - if not built before, build and add info to some kind of db(???)
- use some kind of yaml language
- define build stages, maybe query rpm about build requirements and install
  them all at once
- check if a build requirement is provided by one of the packages to be
  installed and push it back
- build in parallel(difficult since sb2 is qemu-based, there might be some
  locks preventing starting multiple instances)
  maybe try and see if we can modify sb2 to accept multiple targets at once
  and do the parallelization in the vbox itself
- yaml: define what gets installed and what not(do_not_install)

## droidmedia
TODO: It's stupid that people have to switch back to the `HABUILD_SDK` to build
this, but because the libs would get included in the droid-hal package if the
droidmedia+audioflingerglue build targets were build at the same time as
`hybris-hal`, it needs to be this way.  
So let's fix droid-hal to omit droidmedia and audioflingerglue libs when
packaging.
```
make -jXX $(external/droidmedia/detect_build_targets.sh \
  $PORT_ARCH $(gettargetarch))
cd $ANDROID_ROOT
DROIDMEDIA_VERSION=$(git --git-dir external/droidmedia/.git describe --tags | sed -r "s/\-/\+/g")
DEVICE=$HABUILD_DEVICE rpm/dhd/helpers/pack_source_droidmedia-localbuild.sh $DROIDMEDIA_VERSION
mkdir -p hybris/mw/droidmedia-localbuild/rpm
cp rpm/dhd/helpers/droidmedia-localbuild.spec hybris/mw/droidmedia-localbuild/rpm/droidmedia.spec
sed -ie "s/0.0.0/$DROIDMEDIA_VERSION/" hybris/mw/droidmedia-localbuild/rpm/droidmedia.spec
mv hybris/mw/droidmedia-$DROIDMEDIA_VERSION.tgz hybris/mw/droidmedia-localbuild
rpm/dhd/helpers/build_packages.sh --build=hybris/mw/droidmedia-localbuild
rpm/dhd/helpers/build_packages.sh --mw=https://github.com/sailfishos/gst-droid.git
```

## audioflingerglue
```
make -jXX $(external/droidmedia/detect_build_targets.sh \
  $PORT_ARCH $(gettargetarch))
DEVICE=$HABUILD_DEVICE rpm/dhd/helpers/pack_source_audioflingerglue-localbuild.sh
mkdir -p hybris/mw/audioflingerglue-localbuild/rpm
cp rpm/dhd/helpers/audioflingerglue-localbuild.spec hybris/mw/audioflingerglue-localbuild/rpm/audioflingerglue.spec
mv hybris/mw/audioflingerglue-0.0.1.tgz hybris/mw/audioflingerglue-localbuild
rpm/dhd/helpers/build_packages.sh --build=hybris/mw/audioflingerglue-localbuild
rpm/dhd/helpers/build_packages.sh --mw=https://github.com/mer-hybris/pulseaudio-modules-droid-glue.git
```

## droid-hal-version
- check for droid-hal-version-$DEVICE.spec in hybris/
- go there and build the spec file
- deploy with do_not_install
- the version package pulls in basically all the other packages and is the
  last stage before mic

## mic
- make an offline option and keep caches
- make an option to fetch all necessary packages
  -> build a list of all "Requires" and "BuildRequires" with rpm queryspec,
    filter out the packages in hybris/mw/, then download everything
- run mic create fs/loop based on community_adaptation
