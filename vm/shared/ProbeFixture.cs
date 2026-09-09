// Synthetic Windows message-loop fixture. Never a Minecraft benchmark attempt.
using System;
using System.Windows.Forms;
using System.Threading;
class ProbeFixture {
 [STAThread] static void Main(string[] args) {
  var form=new Form();form.Text="Synthetic hang-detector test (NOT Minecraft)";form.Width=650;form.Height=200;
  var label=new Label();label.Text="Synthetic message-loop test only";label.Dock=DockStyle.Fill;form.Controls.Add(label);
  if(args.Length>0 && args[0]=="hang")form.Shown+=delegate { Thread.Sleep(60000); };
  Application.Run(form);
 }
}
