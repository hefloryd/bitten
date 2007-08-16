<h2>Manage Build Configurations</h2><?cs

if admin.config.name ?>
 <form class="mod" id="modconfig" method="post">
  <table summary=""><tr>
   <td class="name"><label>Name:<br />
    <input type="text" name="name" value="<?cs var:admin.config.name ?>" />
   </label></td>
   <td class="label"><label>Label (for display):<br />
    <input type="text" name="label" size="32" value="<?cs
      var:admin.config.label ?>" />
   </label></td>
  </tr><tr>
   <td colspan="2"><fieldset class="iefix">
    <label for="description">Description (you may use <a tabindex="42" href="<?cs
      var:trac.href.wiki ?>/WikiFormatting">WikiFormatting</a> here):</label>
    <p><textarea id="description" name="description" class="wikitext" rows="5" cols="78"><?cs
      var:admin.config.description ?></textarea></p>
    <script type="text/javascript" src="<?cs
      var:chrome.href ?>/common/js/wikitoolbar.js"></script>
   </fieldset></td>
  </tr></table>
  <fieldset id="recipe">
   <legend>Build Recipe</legend>
   <textarea id="recipe" name="recipe" rows="8" cols="78"><?cs
     var:admin.config.recipe ?></textarea>
  </fieldset>
  <fieldset id="repos">
   <legend>Repository Mapping</legend>
   <table summary=""><tr>
    <th><label for="path">Path:</label></th>
    <td colspan="3"><input type="text" name="path" size="48" value="<?cs
      var:admin.config.path ?>" /></td>
   </tr><tr>
    <th><label for="min_rev">Oldest revision:</label></th>
    <td><input type="text" name="min_rev" size="8" value="<?cs
      var:admin.config.min_rev ?>" /></td>
    <th><label for="min_rev">Youngest revision:</label></th>
    <td><input type="text" name="max_rev" size="8" value="<?cs
      var:admin.config.max_rev ?>" /></td>
   </table>
  </fieldset>
  <fieldset>
    <legend>Target Platforms</legend><?cs
    if:len(admin.config.platforms) ?><ul><?cs
     each:platform = admin.config.platforms ?>
      <li><input type="checkbox" name="delete_platform" value="<?cs
       var:platform.id ?>"> <a href="<?cs
       var:platform.href ?>"><?cs var:platform.name ?></a>
      </li><?cs
     /each ?></ul><?cs
    /if ?>
    <div class="buttons">
     <input type="submit" name="new" value="Add target platform" />
     <input type="submit" name="delete" value="Delete selected platforms" />
    </div>
  </fieldset>
  <div class="buttons">
   <input type="submit" name="cancel" value="Cancel" />
   <input type="submit" name="save" value="Save" />
  </div>
 </form><?cs

elif admin.platform.name ?>
 <form class="mod" id="modplatform" method="post">
    <div class="field"><label>Target Platform:
     <input type="text" name="name" value="<?cs var:admin.platform.name ?>" />
    </label></div>
    <fieldset>
     <legend>Rules</legend>
     <table><thead><tr>
      <th>Property name</th><th>Match pattern</th>
     </tr></thead><tbody><?cs
      each:rule = admin.platform.rules ?><tr>
       <td><input type="text" name="property_<?cs var:name(rule) ?>" value="<?cs
        var:rule.property ?>" /></td>
       <td><input type="text" name="pattern_<?cs var:name(rule) ?>" value="<?cs
        var:rule.pattern ?>" /></td>
       <td><input type="submit" name="add_rule_<?cs
         var:name(rule) ?>" value="+" /><input type="submit" name="rm_rule_<?cs
         var:name(rule) ?>" value="-" />
       </td>
      </tr><?cs /each ?>
     </tbody></table>
    </fieldset>
    <div class="buttons">
     <form method="get" action=""><div>
      <input type="hidden" name="action" value="<?cs
       if:admin.platform.exists ?>edit<?cs else ?>new<?cs /if ?>" />
      <input type="hidden" name="platform" value="<?cs
       var:admin.platform.id ?>" />
      <input type="submit" name="cancel" value="Cancel" />
      <input type="submit" name="save" value="<?cs
       if:admin.platform.exists ?>Save<?cs else ?>Add<?cs
       /if ?>" />
     </div></form>
    </div>
 </form><?cs

else ?>
 <form class="addnew" id="addcomp" method="post">
  <fieldset>
   <legend>Add Configuration:</legend>
   <table summary=""><tr>
    <td class="name"><div class="field"><label>Name:<br />
     <input type="text" name="name" size="12" />
    </label></div></td>
    <td class="label"><div class="field"><label>Label:<br />
     <input type="text" name="label" size="22" />
    </label></div></td>
   </tr><tr>
     <td class="path" colspan="2"><div class="field">
      <label>Path:<br /><input type="text" name="path" size="32" /></label>
     </div>
   </tr></table>
   <div class="buttons">
    <input type="submit" name="add" value="Add">
   </div>
  </fieldset>
 </form>

 <form method="POST">
  <table class="listing" id="configlist">
   <thead>
    <tr><th class="sel">&nbsp;</th><th>Name</th>
    <th>Path</th><th>Active</th></tr>
   </thead><?cs each:config = admin.configs ?>
    <tr>
     <td class="sel"><input type="checkbox" name="sel" value="<?cs
       var:config.name ?>" /></td>
     <td class="name"><a href="<?cs var:config.href?>"><?cs
       var:config.label ?></a></td>
     <td class="path"><code><?cs var:config.path ?></code></td>
     <td class="active"><input type="checkbox" name="active" value="<?cs
       var:config.name ?>"<?cs
       if:config.active ?> checked="checked" <?cs /if ?>></td>
    </tr><?cs
   /each ?>
  </table>
  <div class="buttons">
   <input type="submit" name="remove" value="Remove selected items" />
   <input type="submit" name="apply" value="Apply changes" />
  </div>
 </form><?cs

/if ?>
