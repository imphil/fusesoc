import os.path
from fusesoc import utils

from .backend import Backend
class Ise(Backend):

    TCL_FILE_TEMPLATE = """#Auto generated by FuseSoC
project new {design}
project set family {family}
project set device {device}
project set package {package}
project set speed {speed}
project set "Generate Detailed MAP Report" true
"""

    TCL_FUNCTIONS = """
process run "Generate Programming File"
"""

    PGM_FILE_TEMPLATE = """
# Batch script for programming the device using a JTAG interface.
# Used with:
# $ impact -batch {pgm_file}

setMode -bscan
setCable -port auto
addDevice -p 1 -file {bit_file}
program -p 1
saveCDF -file {cdf_file}
quit
"""

    def configure(self, args):
        super(Ise, self).configure(args)
        for i in ['family', 'device', 'package', 'speed']:
            if not i in self.tool_options:
                raise RuntimeError("Missing required option '{}'".format(i))
        self._write_tcl_file()

    def _write_tcl_file(self):
        tcl_file = open(os.path.join(self.work_root, self.name+'.tcl'),'w')

        tcl_file.write(self.TCL_FILE_TEMPLATE.format(
            design               = self.name,
            family               = self.tool_options['family'],
            device               = self.tool_options['device'],
            package              = self.tool_options['package'],
            speed                = self.tool_options['speed']))

        if self.vlogdefine:
            s = 'project set "Verilog Macros" "{}" -process "Synthesize - XST"\n'
            tcl_file.write(s.format('|'.join([k+'='+self._param_value_str(v) for k,v in self.vlogdefine.items()])))

        if self.vlogparam:
            s = 'project set "Generics, Parameters" "{}" -process "Synthesize - XST"\n'
            tcl_file.write(s.format('|'.join([k+'='+self._param_value_str(v, '\\"') for k,v in self.vlogparam.items()])))

        (src_files, incdirs) = self._get_fileset_files()

        if incdirs:
            tcl_file.write('project set "Verilog Include Directories" "{}" -process "Synthesize - XST"\n'.format('|'.join(incdirs)))

        _libraries = []
        for f in src_files:
            if f.file_type == 'tclSource':
                tcl_file.write('source {}\n'.format(f.name))
            elif f.file_type.startswith('verilogSource'):
                tcl_file.write('xfile add {}\n'.format(f.name))
            elif f.file_type == 'UCF':
                tcl_file.write('xfile add {}\n'.format(f.name))
            elif f.file_type == 'BMM':
                tcl_file.write('xfile add {}\n'.format(f.name))
            elif f.file_type.startswith('vhdlSource'):
                if f.logical_name:
                    if not f.logical_name in _libraries:
                        tcl_file.write('lib_vhdl new {}\n'.format(f.logical_name))
                        _libraries.append(f.logical_name)
                    _s = 'xfile add {} -lib_vhdl {}\n'
                    tcl_file.write(_s.format(f.name,
                                             f.logical_name))
                else:
                    tcl_file.write('xfile add {}\n'.format(f.name))
            elif f.file_type == 'user':
                pass

        tcl_file.write('project set top "{}"\n'.format(self.toplevel))
        tcl_file.write(self.TCL_FUNCTIONS)
        tcl_file.close()

    def build_main(self):
        utils.Launcher('xtclsh', [os.path.join(self.work_root, self.name+'.tcl')],
                           cwd = self.work_root,
                           errormsg = "Failed to make FPGA load module").run()

    def run(self, remaining):
        pgm_file_name = os.path.join(self.work_root, self.name+'.pgm')
        self._write_pgm_file(pgm_file_name)
        utils.Launcher('impact', ['-batch', pgm_file_name],
                           cwd = self.work_root,
                           errormsg = "impact tool returned an error").run()

    def _write_pgm_file(self, pgm_file_name):
        pgm_file = open(pgm_file_name,'w')
        pgm_file.write(self.PGM_FILE_TEMPLATE.format(
            pgm_file             = pgm_file_name,
            bit_file             = os.path.join(self.work_root, self.toplevel+'.bit'),
            cdf_file             = os.path.join(self.work_root, self.toplevel+'.cdf')))
        pgm_file.close()