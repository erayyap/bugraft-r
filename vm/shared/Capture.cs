using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
class Capture {
    static string Quote(string s) {
        var b = new StringBuilder("\""); int n = 0;
        foreach(char c in s) {
            if(c == '\\') { n++; continue; }
            if(c == '"') { b.Append('\\', n * 2 + 1); b.Append(c); n = 0; continue; }
            b.Append('\\', n); n = 0; b.Append(c);
        }
        b.Append('\\', n * 2); b.Append('"'); return b.ToString();
    }
    static int Main(string[] args) {
        try {
            if(args.Length == 0) return 125;
            var a = new StringBuilder();
            for(int i=1; i<args.Length; i++) { if(i>1) a.Append(' '); a.Append(Quote(args[i])); }
            var p = new Process();
            p.StartInfo = new ProcessStartInfo(args[0], a.ToString()) {
                UseShellExecute=false, RedirectStandardInput=true,
                RedirectStandardOutput=true, RedirectStandardError=true,
                CreateNoWindow=true, WorkingDirectory=Environment.CurrentDirectory
            };
            p.Start();
            var input = new Thread(delegate() { try { var source=Console.OpenStandardInput(); var buffer=new byte[4096]; int count; while((count=source.Read(buffer,0,buffer.Length))>0) { p.StandardInput.BaseStream.Write(buffer,0,count); p.StandardInput.BaseStream.Flush(); } p.StandardInput.Close(); } catch {} }); input.IsBackground=true; input.Start();
            var output = new Thread(delegate() { using(var f=new FileStream("game-stdout.txt",FileMode.Create,FileAccess.Write,FileShare.ReadWrite)) { var b=new byte[4096]; int n; while((n=p.StandardOutput.BaseStream.Read(b,0,b.Length))>0) { f.Write(b,0,n); f.Flush(); } } }); output.Start();
            var error = new Thread(delegate() { using(var f=new FileStream("game-stderr.txt",FileMode.Create,FileAccess.Write,FileShare.ReadWrite)) { var b=new byte[4096]; int n; while((n=p.StandardError.BaseStream.Read(b,0,b.Length))>0) { f.Write(b,0,n); f.Flush(); } } }); error.Start();
            p.WaitForExit(); output.Join(); error.Join(); return p.ExitCode;
        } catch(Exception e) { File.WriteAllText("capture-error.txt", e.GetType().Name+": "+e.Message); return 125; }
    }
}
