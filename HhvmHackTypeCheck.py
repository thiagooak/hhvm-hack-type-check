import sublime, sublime_plugin
import os, subprocess
from collections import defaultdict

class HhvmHackTypeCheckListener(sublime_plugin.EventListener):
    def on_post_save(self, view):
        if view.settings().get("hhvm_hack_type_check") != True:
            return

        extension = os.path.splitext(view.file_name())[1]
        if extension in view.settings().get("hhvm_hack_file_extensions"):
            view.window().run_command("hhvm_hack_run_type_checker")

class HhvmHackRunTypeCheckerCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.removeMarks()
        output = self.runChecker()
        self.displayTextArea(output)
        self.addMarks(output)

    def runChecker(self):
        directory = os.path.dirname(self.window.active_view().file_name())
        # @TODO should use --json option
        proc = subprocess.Popen(
            [self.window.active_view().settings().get("hhvm_hack_client_cmd")],
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)

        if proc.returncode == 0:
            return ""

        stdout, stderr = proc.communicate()
        return stdout.decode("utf-8")

    def addMarks(self, output):
        # group by file
        files = defaultdict(list)
        output_lines = output.split("\n")
        for output_line in output_lines:
            output_line = output_line.strip()
            parts = output_line.split(":")
            if len(parts) < 2:
                continue
            files[parts[0]].append(parts[1:])

        # apply to each file
        for key in files:
            # @TODO fix mapping between VM and HOST (in case it is running on a VM)
            # @TODO currently we assume that each filename is unique
            view = self.window.find_open_file(os.path.split(key)[1])
            if view == None:
                continue

            lines = []
            for values in files[key]:
                lines.append(int(values[0]))

            regions = self.linesToRegions(view, lines)
            view.add_regions("hhvm-hack", regions, "error", "dot", sublime.HIDDEN | sublime.PERSISTENT)

    def removeMarks(self):
        for view in self.window.views():
            view.erase_regions('hhvm-hack')
            view.erase_regions('mark')

    def displayTextArea(self, text):
        self.output_view = self.window.get_output_panel("textarea")
        self.window.run_command("show_panel", {"panel": "output.textarea"})
        self.output_view.set_read_only(False)
        self.output_view.run_command("append", {"characters": text})
        self.output_view.set_read_only(True)

    def linesToRegions(self, view, lines):
        regions = []
        for line in lines:
            position = view.text_point(line - 1, 0)
            region = sublime.Region(position, position)
            regions.append(region)
        return regions