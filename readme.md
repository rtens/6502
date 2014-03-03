## 6502 Emulator ##

After I found [this very nice tutorial][tutorial] on writing assembler code for the 6502
microprocessor I gave it a try myself at the following CodingDojo. It took a while to wrap
my head around it but at the end of the evening we successfully painted the display blue - not
quite the sphere ray-tracing we originally had in mind.

So I thought the best way to really understand it, would be to implement an emulator for the
processor myself. This is the result.

### Usage ###

To run a program enter the following command. `debug` starts the debugger to step through the
program instruction by instruction.

    python run.py <source_file> [debug]

## Work in Progress ##

The emulator is far from being complete. The most important instructions are implemented, but
many are still missing.

### Acknowledgement ###

I took the snake program from the [tutorial] and part of the test suite from [py65].

[tutorial]: http://skilldrick.github.io/easy6502/
[py65]: https://github.com/mnaberez/py65/