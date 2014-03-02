import assembler, controller, plugins, sys

c = controller.Controller()

plugins.BitmapDisplay(32, 32, 10).register(c, 0x0200)
plugins.RandomNumberGenerator().register(c, 0xfe)

c.run(assembler.Assembler().assemble(open(sys.argv[1], 'r').read()))