# -*- coding: utf-8 -*-


import hil_nxt_hboot_image_compiler.com.netx90_app_iflash_image

import SCons.Script


def __iflash_image_action(target, source, env):
    fVerbose = False
    if 'IFLASHIMAGE_VERBOSE' in env:
        fVerbose = bool(env['IFLASHIMAGE_VERBOSE'])

    strAsicTyp = env['ASIC_TYP']
    if (strAsicTyp != 'NETX90_MPW_APP') and (strAsicTyp != 'NETX90_APP'):
        raise Exception(
            'IFlash images are not possible for ASIC typ "%s".' % strAsicTyp
        )

    netx90_app_iflash_image.patch_image(
        source[0].get_path(),
        target[0].get_path(),
        fVerbose
    )

    return 0


def __iflash_image_emitter(target, source, env):
    env.Depends(target, SCons.Node.Python.Value(str(env['ASIC_TYP'])))

    return target, source


def __iflash_image_string(target, source, env):
    return 'IFlashImage %s' % target[0].get_path()


# ---------------------------------------------------------------------------
#
# Add IFlashImage builder.
#
def ApplyToEnv(env):
    env['IFLASHIMAGE_VERBOSE'] = False

    iflash_image_act = SCons.Action.Action(
        __iflash_image_action,
        __iflash_image_string
    )
    iflash_image_bld = SCons.Script.Builder(
        action=iflash_image_act,
        emitter=__iflash_image_emitter,
        suffix='.bin',
        single_source=1)
    env['BUILDERS']['IFlashImage'] = iflash_image_bld
