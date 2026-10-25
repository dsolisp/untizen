using System;
using System.Runtime.InteropServices;
public static class Probe {
 [DllImport("libcapi-appfw-app-operation-tv.so.0")] static extern int app_operation_get_current_app(string operation,out IntPtr app);
 [DllImport("libcapi-appfw-app-operation-tv.so.0")] static extern int app_operation_set_current_app(string operation,string app);
 [DllImport("libsource-api.so")] static extern IntPtr get_source_list();
 [DllImport("libvconf.so.0")] static extern int vconf_get_int(string key,out int value);
 [DllImport("libc.so.6")] static extern void free(IntPtr p);
 [DllImport("libcapi-media-sound-manager-tv.so.0")] static extern int sound_manager_get_master_volume(out int value);
 [DllImport("libcapi-media-sound-manager-tv.so.0")] static extern int sound_manager_get_master_mute(out int value);
 public static int Main(string[] args) {
  try {
   if(args.Length==2 && args[0]=="set-home") {int s=app_operation_set_current_app("http://tizen.org/appcontrol/operation/main",args[1]); Console.WriteLine("set_home="+s);return s==0?0:1;}
   if(args.Length==1 && args[0]=="state") {int v,m;int vr=sound_manager_get_master_volume(out v),mr=sound_manager_get_master_mute(out m);Console.WriteLine("volume="+v+" volume_result="+vr+" mute="+m+" mute_result="+mr);return vr==0&&mr==0?0:1;}
   IntPtr p;int r=app_operation_get_current_app("http://tizen.org/appcontrol/operation/main",out p);
   Console.WriteLine("home_result="+r+" home="+(p==IntPtr.Zero?"null":Marshal.PtrToStringAnsi(p)));if(p!=IntPtr.Zero)free(p);
   p=get_source_list();Console.WriteLine("sources="+(p==IntPtr.Zero?"null":Marshal.PtrToStringAnsi(p)));
   int source; r=vconf_get_int("memory/system/source_type",out source);Console.WriteLine("current_source_result="+r+" current_source="+source);
   return 0;
  } catch(Exception e) {Console.WriteLine(e);return 1;}
 }
}
