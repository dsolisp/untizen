using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

// The HDMI inputs Quiet Home features, in catalogue order. The hero card and the
// dock reorder themselves around the recents journal, so every mark ships in a
// hero cut (logo on the right half, text on the left) and a portrait cut.
public sealed class InputDef
{
 public string Name,Tagline,Description,Hero,Portrait,Dock;
 public int Source;
 public string Action{get{return "hdmi:"+Source;}}
}

public static class Inputs
{
 public static readonly List<InputDef> All=new List<InputDef>{
  new InputDef{Name="PS5",Source=14,Tagline="Let's play.",Description="Console · HDMI",Hero="hero-ps5.svg",Portrait="portrait-ps5.svg",Dock="ps5"},
  new InputDef{Name="Xbox",Source=13,Tagline="Game on.",Description="Console · HDMI",Hero="hero-xbox.svg",Portrait="feature-xbox.svg",Dock="xbox"},
  new InputDef{Name="PC",Source=16,Tagline="Back to it.",Description="Computer · HDMI",Hero="hero-pc.svg",Portrait="feature-hdmi.svg",Dock="pc"}};
 public static InputDef BySource(int source){return All.Find(i=>i.Source==source);}
 public static InputDef ByAction(string action){return All.Find(i=>i.Action==action);}
 // Hero first: the input the TV is on right now, then the journal, then catalogue order.
 public static List<InputDef> Ordered(List<string> journal,int liveSource)
 {
  var order=new List<InputDef>();
  var live=BySource(liveSource);
  if(live!=null)order.Add(live);
  foreach(var action in journal){var input=ByAction(action);if(input!=null&&!order.Contains(input))order.Add(input);}
  foreach(var input in All)if(!order.Contains(input))order.Add(input);
  return order;
 }
}

// Newest-first journal of what the household actually opened. Only launches made
// from Quiet Home land here; the live input comes from vconf at resume time.
// Ceiling: launches started outside the launcher (voice, Smart Hub) stay invisible
// until this journal is replaced by the TV's own usage history.
public static class Recents
{
 public const int DockCount=5, JournalCap=24;
 // First-run dock, before the journal knows anything about the household.
 public static readonly List<string> DefaultDock=new List<string>{
  "app:org.tizen.netflix-app","app:com.samsung.tv.cobalt-yt","app:org.tizen.primevideo","hdmi:14","hdmi:13"};
 public static bool IsAction(string entry)
 {
  if(entry==null)return false;
  int colon=entry.IndexOf(':');
  return colon>0&&colon<entry.Length-1&&(entry.StartsWith("app:")||entry.StartsWith("hdmi:"));
 }
 public static List<string> Load(string path)
 {
  try{
   var loaded=JsonSerializer.Deserialize<List<string>>(File.ReadAllText(path));
   var journal=new List<string>();
   if(loaded!=null)foreach(var entry in loaded)if(IsAction(entry)&&!journal.Contains(entry))journal.Add(entry);
   return journal;
  }catch{return new List<string>();}
 }
 public static void Save(string path,List<string> journal)
 {
  try{File.WriteAllText(path,JsonSerializer.Serialize(journal));}catch{}
 }
 public static List<string> Record(List<string> journal,string action)
 {
  var next=new List<string>{action};
  foreach(var entry in journal)if(entry!=action&&next.Count<JournalCap)next.Add(entry);
  return next;
 }
 // Five tiles, newest first: journal hits the household can actually open, then
 // the first-run defaults, then whatever the catalogue allows.
 public static List<string> DockActions(List<string> journal,List<string> allowed)
 {
  var dock=new List<string>();
  foreach(var action in journal.Concat(DefaultDock).Concat(allowed))
  {
   if(dock.Count>=DockCount)break;
   if(allowed.Contains(action)&&!dock.Contains(action))dock.Add(action);
  }
  return dock;
 }
}
