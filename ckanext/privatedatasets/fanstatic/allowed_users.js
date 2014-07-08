/* Dataset allowed_users and adquire_url toggler
 * allowed_users, adquire_url and searchable can only be active when a 
 * user attempts to create a private dataset outside an organization 
 */

this.ckan.module('allowed-users', function ($, _) {
  return {
    initialize: function() {
      $('#field-private').on('change', this._onChange);
      $('#field-organizations').on('change', this._onChange);
      this._onChange();
    },
    _onChange: function() {
      var ds_private = $('#field-private').val();

      if (ds_private == "True") {
        $('#field-allowed_users').prop('disabled', false);  //Enable
        $('#field-adquire_url').prop('disabled', false);    //Enable
        $('#field-searchable').prop('disabled', false);    //Enable
      } else {
        $('#field-allowed_users').prop('disabled', true);   //Disable
        $('#field-adquire_url').prop('disabled', true);     //Disable
        $('#field-searchable').prop('disabled', true);      //Disable
        
        //Remove previous values
        $('#s2id_field-allowed_users .select2-search-choice').remove();
        $('#field-allowed_users').val('');
        $('#field-adquire_url').val('');
        $('#field-searchable').val('True');
      }
    }
  };
});
