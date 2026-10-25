using System;
using System.Collections.Generic;
using System.IO;

static class CatalogTests
{
    static void Equal(int expected, int actual, string context)
    {
        if (expected != actual) throw new Exception(context + ": expected " + expected + ", got " + actual);
    }
    public static int Main(string[] args)
    {
        var catalog = AppLibrary.Load(args[0]);
        if (catalog.Count < 2) throw new Exception("Catalog unexpectedly small");
        Equal(-1, AppLibrary.Move(31, 0, "Up"), "top row returns to tabs");
        Equal(15, AppLibrary.Move(31, 10, "Down"), "last row enters next page");
        Equal(25, AppLibrary.Move(31, 30, "Up"), "partial page returns to matching previous column");
        Equal(30, AppLibrary.Move(31, 29, "Down"), "last partial page clamps column");
        Equal(11, AppLibrary.Move(12, 9, "Down"), "partial bottom row clamps column");
        Equal(11, AppLibrary.Move(12, 11, "Right"), "last item remains selected");
        Equal(-1, AppLibrary.Move(0, 0, "Down"), "empty catalog");
        for (int count = 1; count < 48; count++)
            for (int item = 0; item < count; item++)
                foreach (var key in new[] {"Left", "Right", "Up", "Down"})
                {
                    int next = AppLibrary.Move(count, item, key);
                    if (next < -1 || next >= count) throw new Exception("Out of bounds navigation");
                }
        string tmp = Path.GetTempFileName();
        try
        {
            foreach (string json in new[] {
                "[{\"Name\":\"Bad\",\"Id\":\"one\",\"Asset\":\"../escape.svg\",\"Width\":100,\"Height\":50}]",
                "[{\"Name\":\"Bad\",\"Id\":\"one\",\"Asset\":\"ok.svg\",\"Width\":100,\"Height\":50,\"Crop\":[0.8,0,0.4,1]}]",
                "[{\"Name\":\"A\",\"Id\":\"one\",\"Asset\":\"ok.svg\",\"Width\":100,\"Height\":50},{\"Name\":\"B\",\"Id\":\"one\",\"Asset\":\"ok.svg\",\"Width\":100,\"Height\":50}]"
            })
            {
                File.WriteAllText(tmp, json);
                bool rejected = false;
                try { AppLibrary.Load(tmp); } catch (InvalidDataException) { rejected = true; }
                if (!rejected) throw new Exception("Invalid catalog accepted");
            }
        }
        finally { File.Delete(tmp); }
        // Recents: journal recording, hero order and the dock fill.
        var journal = Recents.Record(new List<string>(), "hdmi:14");
        journal = Recents.Record(journal, "app:org.tizen.netflix-app");
        journal = Recents.Record(journal, "hdmi:14");
        if (journal[0] != "hdmi:14" || journal[1] != "app:org.tizen.netflix-app" || journal.Count != 2)
            throw new Exception("Record must move repeats to the front");
        var capped = new List<string>();
        for (int i = 0; i < Recents.JournalCap + 5; i++) capped = Recents.Record(capped, "app:id-" + i);
        Equal(Recents.JournalCap, capped.Count, "journal caps");
        if (capped[0] != "app:id-" + (Recents.JournalCap + 4)) throw new Exception("journal stays newest first");
        var ordered = Inputs.Ordered(new List<string> {"hdmi:13"}, 16);
        if (ordered[0].Source != 16 || ordered[1].Source != 13 || ordered[2].Source != 14)
            throw new Exception("live input wins, then journal, then catalogue");
        if (Inputs.Ordered(new List<string>(), 0)[0].Source != 14)
            throw new Exception("catalogue order without recents");
        var allowed = new List<string> {"app:netflix", "app:yt", "app:prime", "hdmi:14", "hdmi:13", "hdmi:16"};
        var dock = Recents.DockActions(new List<string> {"hdmi:13", "app:yt", "app:gone"}, allowed);
        Equal(5, dock.Count, "dock fills to five");
        if (dock[0] != "hdmi:13" || dock[1] != "app:yt") throw new Exception("dock follows the journal");
        if (dock[2] != "hdmi:14" || dock[3] != "app:netflix" || dock[4] != "app:prime")
            throw new Exception("dock falls back to first-run defaults without duplicates");
        string recentsTmp = Path.GetTempFileName();
        try
        {
            Recents.Save(recentsTmp, dock);
            Equal(dock.Count, Recents.Load(recentsTmp).Count, "journal roundtrip");
            File.WriteAllText(recentsTmp, "{not json");
            Equal(0, Recents.Load(recentsTmp).Count, "corrupt journal starts empty");
        }
        finally { File.Delete(recentsTmp); }
        string sourcesTmp = Path.GetTempFileName();
        try
        {
            File.WriteAllText(sourcesTmp,
                "[{\"Name\":\"Switch\",\"Source\":15,\"Tagline\":\"Docked.\",\"Description\":\"Console · HDMI\",\"Hero\":\"hero.svg\",\"Portrait\":\"portrait.svg\",\"Dock\":\"switch\"}]");
            Inputs.Load(sourcesTmp);
            Equal(1, Inputs.All.Count, "sources.json replaces the built-in list");
            if (Inputs.BySource(15)==null || Inputs.BySource(14)!=null)
                throw new Exception("loaded sources must replace the defaults");
            Inputs.Reset();
            if (Inputs.BySource(14)==null) throw new Exception("Reset restores the built-in HDMI list");
        }
        finally { File.Delete(sourcesTmp); Inputs.Reset(); }
        if (StatePaths.Prefer("/new","/old",p=>p=="/new")!="/new")
            throw new Exception("Prefer the new path when it exists");
        if (StatePaths.Prefer("/new","/old",p=>p=="/old")!="/old")
            throw new Exception("Prefer the quiet-home leftover when the new path is absent");
        if (StatePaths.Prefer("/new","/old",p=>false)!="/new")
            throw new Exception("Write the new path when neither file exists");
        Console.WriteLine("Catalog, navigation, invalid-input and recents checks passed.");
        return 0;
    }
}
