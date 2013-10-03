/********************************************************************** 
 Freeciv - Copyright (C) 2009 - Andreas Røsdal   andrearo@pvv.ntnu.no
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 2, or (at your option)
   any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
***********************************************************************/


/****************************************************************
 The "options" file handles actual "options", and also view options,
 message options, dialog/report settings, cma settings, server settings,
 and global worklists.
*****************************************************************/

/** Defaults for options normally on command line **/

var default_user_name = "";
var default_server_host = "localhost";
//var  default_server_port = DEFAULT_SOCK_PORT;
//var default_metaserver = META_URL;
var default_theme_name = "human";
var default_tileset_name = "";
var default_sound_set_name = "stdsounds";
var default_sound_plugin_name = "";

var save_options_on_exit = TRUE;
var fullscreen_mode = FALSE;

/** Local Options: **/

var solid_color_behind_units = FALSE;
var sound_bell_at_new_turn = FALSE;
var  smooth_move_unit_msec = 30;
var smooth_center_slide_msec = 200;
var do_combat_animation = TRUE;
var ai_manual_turn_done = TRUE;
var auto_center_on_unit = TRUE;
var auto_center_on_combat = FALSE;
var auto_center_each_turn = TRUE;
var wakeup_focus = TRUE;
var goto_into_unknown = TRUE;
var center_when_popup_city = TRUE;
var concise_city_production = FALSE;
var auto_turn_done = FALSE;
var meta_accelerators = TRUE;
var ask_city_name = TRUE;
var popup_new_cities = TRUE;
var popup_caravan_arrival = TRUE;
var keyboardless_goto = TRUE;
var enable_cursor_changes = TRUE;
var separate_unit_selection = FALSE;
var unit_selection_clears_orders = TRUE;
var highlight_our_names = "yellow";

/* This option is currently set by the client - not by the user. */
var update_city_text_in_refresh_tile = TRUE;

var draw_city_outlines = TRUE;
var draw_city_output = FALSE;
var draw_map_grid = FALSE;
var draw_city_names = TRUE;
var draw_city_growth = TRUE;
var draw_city_productions = FALSE;
var draw_city_buycost = FALSE;
var draw_city_traderoutes = FALSE;
var draw_terrain = TRUE;
var draw_coastline = FALSE;
var draw_roads_rails = TRUE;
var draw_irrigation = TRUE;
var draw_mines = TRUE;
var draw_fortress_airbase = TRUE;
var draw_specials = TRUE;
var draw_pollution = TRUE;
var draw_cities = TRUE;
var draw_units = TRUE;
var draw_focus_unit = FALSE;
var draw_fog_of_war = TRUE;
var draw_borders = TRUE;
var draw_full_citybar = TRUE;
var draw_unit_shields = TRUE;
var player_dlg_show_dead_players = TRUE;
var reqtree_show_icons = TRUE;
var reqtree_curved_lines = FALSE;

/* gui-gtk-2.0 client specific options. */
var gui_gtk2_map_scrollbars = FALSE;
var gui_gtk2_dialogs_on_top = TRUE;
var gui_gtk2_show_task_icons = TRUE;
var gui_gtk2_enable_tabs = TRUE;
var gui_gtk2_better_fog = TRUE;
var gui_gtk2_show_chat_message_time = FALSE;
var gui_gtk2_split_bottom_notebook = FALSE;
var gui_gtk2_new_messages_go_to_top = FALSE;
var gui_gtk2_show_message_window_buttons = TRUE;
var gui_gtk2_metaserver_tab_first = FALSE;
var gui_gtk2_allied_chat_only = FALSE;
var gui_gtk2_small_display_layout = FALSE;

function init_options_dialog() 
{
  if (overview_active) {
    $("#show_overview_button").hide();
  } else {
    $("#show_overview_button").show();
  }

  if (unitpanel_active) {
    $("#show_unit_button").hide();
  } else {
    $("#show_unit_button").show();
  }

  if (chatbox_active) {
    $("#show_message_button").hide();
  } else {
    $("#show_message_button").show();
  }

  $("#save_button").button("option", "label", "Save Game");

  $("#timeout_setting").val(game_info['timeout']);
  $("#metamessage_setting").val(game_info['meta_message']);


  $('#metamessage_setting').change(function() {
    var test_packet = {"type" : packet_chat_msg_req, "message" : "/metamessage " + $('#metamessage_setting').val()};
    var myJSONText = JSON.stringify(test_packet);
    send_request (myJSONText);
  });

  $('#metamessage_setting').bind('keyup blur',function(){ 
    var cleaned_text = $(this).val().replace(/[^a-zA-Z\s\-]/g,'');
    if ($(this).val() != cleaned_text) {
      $(this).val( cleaned_text ); }
    }
  );

  $('#timeout_setting').change(function() {
    var test_packet = {"type" : packet_chat_msg_req, "message" : "/set timeout " + $('#timeout_setting').val()};
    var myJSONText = JSON.stringify(test_packet);
    send_request (myJSONText);
  });


}
