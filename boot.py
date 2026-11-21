# boot.py — 上电入口。异常时保留 REPL，不自动重启循环。
import config

try:
    import gc
    import machine

    print(
        "#DBG t=0 ev=boot cause=%s heap=%d freq=%d"
        % (machine.reset_cause(), gc.mem_free(), machine.freq())
    )
except Exception as exc:
    print("#DBG ev=boot_fail e=%r" % (exc,))

if config.AUTO_START:
    try:
        from main import run

        run()
    except Exception as exc:
        import sys

        print("应用启动失败，保留 REPL：")
        sys.print_exception(exc)
else:
    print("AUTO_START=False；硬件自检：import tests.test_hardware")
