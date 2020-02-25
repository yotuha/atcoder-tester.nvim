import neovim
from html.parser import HTMLParser
import urllib.request
import re
import subprocess
import json


@neovim.plugin
class Main(object):
    def __init__(self, vim):
        self.vim = vim
        self.opts = "{'relative': 'editor', 'width': 30, 'height': 30, 'col': &columns, 'row': 0, 'style': 'minimal'}"
        self.running = False
        self.correct_num = 0
        self.sample_num = 0

    def parse_html(self, body):
        repatter = re.compile(r'<h3>入力例.*?</pre>', flags=re.DOTALL)
        in_samples = repatter.findall(body)
        repatter = re.compile(r'<h3>出力例.*?</pre>', flags=re.DOTALL)
        out_samples = repatter.findall(body)
        repatter = re.compile(r'^.*<pre>(.*)</pre>.*$', flags=re.DOTALL)
        in_samples = list(map(lambda string: repatter.sub('\\1', string), in_samples))
        out_samples = list(map(lambda string: repatter.sub('\\1', string), out_samples))
        samples = [(i, o) for i, o in zip(in_samples, out_samples)]
        return samples


    def get_sample_data(self, contest_name, task_name):
        url = 'https://atcoder.jp/contests/{0}/tasks/{0}_{1}'.format(contest_name, task_name)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            body = res.read().decode('utf-8')
            samples = self.parse_html(body)
        return samples


    def update_correct(self):
        buf_str = 'Correct: {} / {}'.format(self.correct_num, self.sample_num)
        self.vim.command('call nvim_buf_set_lines(g:AtcoderTester_buf, 0, 1, v:true, ["{}"])'.format(buf_str))
        if self.correct_num == self.sample_num:
            self.vim.command('call nvim_buf_add_highlight(g:AtcoderTester_buf, 0, "PmenuSel", 0, 0, -1)')
        else:
            self.vim.command('call nvim_buf_add_highlight(g:AtcoderTester_buf, 0, "IncSearch", 0, 0, -1)')


    def check_correct(self, ans1, ans2):
        ans1 = ans1.replace('\r', '').replace('\n', '').split()
        ans2 = ans2.replace('\r', '').replace('\n', '').split()
        if ans1 == ans2:
            self.correct_num += 1
            self.update_correct()


    def insert_sample_string_to_buffer(self, string):
        line_num = self.vim.eval('nvim_buf_line_count(g:AtcoderTester_buf)')
        self.vim.command('call nvim_buf_set_lines(g:AtcoderTester_buf, -1, -1, v:true, {})'.format(json.dumps(string.split('\n'))))
        self.vim.command('call nvim_buf_add_highlight(g:AtcoderTester_buf, 0, "LineNr", {}, 0, -1)'.format(line_num))


    def test_code(self, samples):
        ans = []
        for sample in samples:
            command = 'echo "{}" | ./a.out'.format(sample[0])
            process = subprocess.Popen(
                    command,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    shell=True
                    )
            res = process.communicate()[0].decode('utf-8')
            self.check_correct(res, sample[1])
            buf_strs = [''] * 3
            buf_strs[0] = 'IN:\n{}'.format(sample[0]).replace('\r', '')
            buf_strs[1] = 'OUT:\n{}'.format(res).replace('\r', '')
            buf_strs[2] = 'ANS:\n{}\n'.format(sample[1]).replace('\r', '')
            for string in buf_strs:
                self.insert_sample_string_to_buffer(string)


    @neovim.function('AtcoderTester_run', eval='expand("%")')
    def do(self, args, filename):
        try:
            if self.running:
                self.vim.command('echo "already running do()"')
                return
            self.running = True
            win_id = self.vim.eval('bufwinid(g:AtcoderTester_buf)')
            contest_name, task_name = filename.split('/')[-1].split('.')[0].split('-')
            samples = self.get_sample_data(contest_name, task_name)
            self.vim.command('call nvim_buf_set_lines(g:AtcoderTester_buf, 0, -1, v:true, ["", ""])')
            self.sample_num = len(samples)
            self.correct_num = 0
            self.update_correct()
            if win_id == -1:
                self.vim.command('let g:AtcoderTester_win = nvim_open_win(g:AtcoderTester_buf, v:true, {})'.format(self.opts))
            else:
                self.vim.command('call win_gotoid(g:AtcoderTester_win)')
            self.test_code(samples)
            self.running = False
        except:
            win_id = self.vim.eval('bufwinid(g:AtcoderTester_buf)')
            if win_id != -1:
                self.vim.command('call nvim_win_close(g:AtcoderTester_win, v:true)')
            self.vim.command('echo "do() failed"')
            self.running = False
