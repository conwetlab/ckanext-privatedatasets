/* Dataset visibility toggler
 * When no organization is selected in the org dropdown then set visibility to
 * public always and disable dropdown
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
      var organization = $('#field-organizations').val();

      if (ds_private == "True" && !organization) {
        $('#field-allowed_users').prop('disabled', false);  //Enable
        $('#field-adquire_url').prop('disabled', false);    //Enable
      } else {
        $('#field-allowed_users').prop('disabled', true);   //Disable
        $('#field-adquire_url').prop('disabled', true);     //Disable
        
        //Remove previous values
        $('#s2id_field-allowed_users .select2-search-choice').remove();
        $('#field-allowed_users').val('');
        $('#field-adquire_url').val('');
      }
    }
  };
});
