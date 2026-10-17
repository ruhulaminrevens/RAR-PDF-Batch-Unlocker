"""Set a visible CI desktop large enough for authentic, unclipped screenshots."""
import sys
if sys.platform=='win32':
    import win32api
    import win32con
    current=win32api.EnumDisplaySettings(None,win32con.ENUM_CURRENT_SETTINGS)
    if current.PelsWidth<1400 or current.PelsHeight<1060:
        for width,height in [(1920,1080),(1600,1200),(1920,1200)]:
            mode=win32api.EnumDisplaySettings(None,win32con.ENUM_CURRENT_SETTINGS)
            mode.PelsWidth=width;mode.PelsHeight=height
            mode.Fields=win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
            if win32api.ChangeDisplaySettings(mode,0)==win32con.DISP_CHANGE_SUCCESSFUL:break
    final=win32api.EnumDisplaySettings(None,win32con.ENUM_CURRENT_SETTINGS)
    print(f'QA desktop: {final.PelsWidth}x{final.PelsHeight}')
    if final.PelsWidth<1400 or final.PelsHeight<1060:raise RuntimeError('CI desktop cannot fit the capture; refusing clipped screenshot evidence')
