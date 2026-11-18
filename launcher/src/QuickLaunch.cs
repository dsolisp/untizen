using System;
using System.IO;
using System.Runtime.InteropServices;
using Tizen.NUI;
using Tizen.Applications;
// The vendor boot unit expects this application to accept its preload request.
// Acknowledge it and exit; interactive requests open the existing Quiet Home process.
public sealed class QuickLaunch : NUIApplication {
 [DllImport("libcapi-appfw-app-control.so.0")] static extern int app_control_create(out IntPtr c);
 [DllImport("libcapi-appfw-app-control.so.0")] static extern int app_control_set_app_id(IntPtr c,string id);
 [DllImport("libcapi-appfw-app-control.so.0")] static extern int app_control_set_operation(IntPtr c,string op);
 [DllImport("libcapi-appfw-app-control.so.0")] static extern int app_control_add_extra_data(IntPtr c,string key,string val);
 [DllImport("libcapi-appfw-app-control.so.0")] static extern int app_control_send_launch_request(IntPtr c,IntPtr cb,IntPtr data);
 [DllImport("libcapi-appfw-app-control.so.0")] static extern int app_control_destroy(IntPtr c);
 bool asked;
 Tizen.NUI.Timer idle;
 protected override void OnCreate(){base.OnCreate();Window.Default.Hide();
  // The vendor boot unit starts this assembly and may never send it an app-control
  // request, which left a 79 MB settings process resident from power-on. Nothing
  // asked us anything within 3 seconds, so hand that memory back. A real key press
  // cold-starts the app and its request arrives immediately, so the timer never fires.
  idle=new Tizen.NUI.Timer(3000);
  idle.Tick+=(s,e)=>{if(!asked)Exit();return false;};
  idle.Start();
 }
 protected override void OnAppControlReceived(AppControlReceivedEventArgs e){
  base.OnAppControlReceived(e);asked=true;string kind;bool preload=e.ReceivedAppControl.ExtraData.TryGet("launch_type",out kind)&&kind=="preload";
  int result=0;
  if(!preload){IntPtr c;result=app_control_create(out c);if(result==0){try{
   result=app_control_set_app_id(c,"com.samsung.tv.bixby-promotion");
   if(result==0)result=app_control_set_operation(c,"http://tizen.org/appcontrol/operation/default");
   if(result==0)result=app_control_add_extra_data(c,"quiet_page","settings");
   if(result==0)result=app_control_send_launch_request(c,IntPtr.Zero,IntPtr.Zero);
  }finally{app_control_destroy(c);}}}
  try{File.WriteAllText("/tmp/untizen-bridge.txt",DateTime.UtcNow.ToString("o")+"\npreload="+preload+"\nresult="+result+"\n");}catch{}
  Exit();
 }
 public static void Main(string[] args){using(var app=new QuickLaunch())app.Run(args);}
}
