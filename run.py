import sys
from lib import assembler, plugins, controller, debugger

program = open(sys.argv[1], 'r').read()

if len(sys.argv) > 2:
    debugger.Debugger().debug(program)

else:
    c = controller.Controller()

    plugins.BitmapDisplay(32, 32, 10).register(c, 0x0200, 0xff, 0xf0)
    plugins.RandomNumberGenerator().register(c, 0xfe)
    plugins.Out().register(c, 0xfd)

    c.run(assembler.Assembler().assemble(program))