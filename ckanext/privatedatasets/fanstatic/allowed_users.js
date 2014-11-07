/*
 * (C) Copyright 2014 CoNWeT Lab., Universidad Politécnica de Madrid
 *
 * This file is part of CKAN Private Dataset Extension.
 *
 * CKAN Private Dataset Extension is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * CKAN Private Dataset Extension is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public
 * License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with CKAN Private Dataset Extension. If not, see
 * <http://www.gnu.org/licenses/>.
 *
 */

/* Dataset allowed_users, searchable and acquire_url toggler
 * allowed_users, acquire_url and searchable can only be active when a 
 * user attempts to create a private dataset
 */

this.ckan.module('allowed-users', function ($, _) {
  return {
    initialize: function() {
      this.original_acquire_url = $('[name=acquire_url]').val();
      $('#field-private').on('change', this._onChange);
      this._onChange(); //Initial
    },
    _onChange: function() {
      var ds_private = $('#field-private').val();

      if (ds_private == 'True') {
        $('#field-allowed_users_str').prop('disabled', false);      //Enable
        $('#field-acquire_url').prop('disabled', false);            //Enable
        $('#field-searchable').prop('disabled', false);             //Enable
        $('[name=acquire_url]').val(this.original_acquire_url);     //Set previous acquire URL
      } else {
        $('#field-allowed_users_str').prop('disabled', true);       //Disable
        $('#field-acquire_url').prop('disabled', true);             //Disable
        $('#field-searchable').prop('disabled', true);              //Disable
        
        //Remove previous values
        $('#field-allowed_users_str').select2('val', '');
        this.original_acquire_url = $('[name=acquire_url]').val();  //Get previous value
        $('[name=acquire_url]').val('');                            //Acquire URL should be reseted
        $('#field-searchable').val('True');
      }
    }
  };
});
