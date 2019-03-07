#!/usr/bin/python

import os
import io
import sys

class EnumNameValue:
    def __init__(self, name, value):
        self.name = name
        self.value = value

class FriendlyEnum:
    def __init__(self, header_path):
        header = []
        with io.open(header_path, 'r', encoding='utf-8-sig') as f:
            header = f.readlines()
        self.file_name = os.path.splitext(os.path.basename(header_path))[0]
        self.implementation = os.path.splitext(header_path)[0] + '.cpp'
        self.start_lines = []
        self.end_lines = []
        self.enum_name = None
        self.enum_values = []
        self.to_string = None
        self.to_stream = None
        self.parse = None
        self.parse_header(header)

    def parse_header(self, header_lines):
        result = []
        decls = []
        copy_lines = self.start_lines
        for line in header_lines:
            sline = line.strip()
            if sline.startswith('//'):
                continue
            if sline.startswith('#'):
                continue
            #print ('>{0}'.format(sline))
            if sline.startswith('enum class'):
                self.enum_name = sline.split(' ')[2]
                copy_lines = None
                continue
            if copy_lines is None:
                if sline == '{':
                    continue
                elif sline.startswith('}'):
                    copy_lines = self.end_lines
                else:
                    sline = sline.rstrip(',').strip()
                    if len(sline) == 0:
                        continue
                    parts = sline.split('=')
                    if len(parts) > 1:
                        self.enum_values.append(EnumNameValue(parts[0].strip(), parts[1].strip()))
                    else:
                        self.enum_values.append(EnumNameValue(sline, None))
            if copy_lines is not None:
                if copy_lines == self.end_lines and sline.endswith(';'):
                    decls.append(line.rstrip().rstrip('; '))
                else:
                    l = line.rstrip()
                    if len(l) > 0:
                        copy_lines.append(l)
        # function declarations
        for decl in decls:
            if decl.startswith('const char') or decl.startswith('std::string '):
                self.to_string = decl
                continue
            if decl.startswith('std::ostream'):
                self.to_stream = decl
                continue
            if decl.startswith(self.enum_name):
                self.parse = decl
                continue
        # unknown
        self.unknown = self.enum_values[-1]
        for env in self.enum_values:
            if env.name in ['Unknown', 'Undefined', 'Error']:
                self.unknown = env
                break
    
    def get_last_param_name(self, decl):
        decl = decl.rstrip().rstrip(';').rstrip(')')
        decl = decl.split('(')[-1]
        parts = decl.split(',')
        if len(parts) > 0:
            decl = parts[-1].strip()
        parts = decl.split('&')
        if len(parts) > 0:
            decl = parts[-1].strip()
        # std::string value | EnumType value
        decl = decl.split(' ')[-1]
        return decl

    def get_method_name(self, decl):
        decl = decl.rstrip().rstrip(';').rstrip(')')
        decl = decl.split('(')[0]
        parts = decl.split('*')
        if len(parts) > 0:
            decl = parts[-1].strip()
        parts = decl.split('&')
        if len(parts) > 0:
            decl = parts[-1].strip()
        parts = decl.split(' ')
        if len(parts) > 0:
            decl = parts[-1].strip()
        return decl

    def generate_cpp(self):
        lines = [
            '#include "{0}.h"'.format(self.file_name),
            '#include <map>',
            '#include <sstream>',
            '#include <iostream>',
            ''
        ]
        # start
        for line in self.start_lines:
            lines.append(line)
        # to string
        if self.to_string:
            pname = self.get_last_param_name(self.to_string)
            lines.append(self.to_string)
            lines.append('{')
            lines.append('    switch ({0})'.format(pname))
            lines.append('    {')
            for env in self.enum_values:
                lines.append('    case {0}::{1}:'.format(self.enum_name, env.name))
                lines.append('        return "{0}";'.format(env.name))
            lines.append('    }')
            lines.append('    // Unreachable code')
            lines.append('    return "{0}";'.format(self.unknown.name))
            lines.append('}')
            lines.append('')
        # operator <<
        if self.to_stream:
            pname = self.get_last_param_name(self.to_stream)
            lines.append(self.to_stream)
            lines.append('{')
            lines.append('    return os << {0}(value);'.format(self.get_method_name(self.to_string)))
            lines.append('}')
            lines.append('')
        # parse
        if self.parse:
            pname = self.get_last_param_name(self.parse)
            sorted_enums = sorted(self.enum_values, key=lambda env: env.name)
            lines.append(self.parse)
            lines.append('{')
            lines.append('    static std::map<std::string, {0}> nameToValue ='.format(self.enum_name))
            lines.append('    {')
            for idx in range(len(sorted_enums)):
                env = sorted_enums[idx]
                sep = ','
                if idx == len(sorted_enums) - 1:
                    sep = ''
                lines.append('        {{ "{1}", {0}::{1} }}{2}'.format(self.enum_name, env.name, sep))
            lines.append('    };')
            lines.append('    auto it = nameToValue.find({0});'.format(pname))
            lines.append('    if (it == nameToValue.end())')
            lines.append('    {')
            lines.append('        return {0}::{1};'.format(self.enum_name, self.unknown.name))
            lines.append('    }')
            lines.append('    return it->second;')
            lines.append('}')
            lines.append('')
        # end
        for line in self.end_lines:
            lines.append(line)
        return '\n'.join(lines)

    def write_cpp(self, content):
        current_content = None
        with io.open(self.implementation, mode="r", encoding="utf-8") as f:
            current_content = f.read()
        if content == current_content:
            print('The file {0} did not change'.format(self.implementation))
        else:
            with io.open(self.implementation, mode="w", encoding="utf-8") as f:
                f.write(content)

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        if not arg.endswith('.h'):
            print ('Ignoring: {0}'.format(arg))
        fe = FriendlyEnum(arg)
        content = fe.generate_cpp()
        fe.write_cpp(content)
