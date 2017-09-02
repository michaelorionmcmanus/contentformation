import tasks
import yaml


def test_extract_interface_controls_from_schema():
    input_schema = f'''
        contentTypes:
          post:
            name: Post
            description: A post content
            displayField: title
            fields:
                -
                  id: content
                  interface:
                    settings:
                      helpText: Primary Post Content
                    widgetId: markdown
                  localized: true
                  name: Content
                  required: true
                  type: Text
                  validations: []
                -
                  id: media
                  interface:
                    widgetId: assetLinkEditor
                  linkType: Asset
                  localized: true
                  name: Media
                  type: Link
                  validations: []
                -
                  disabled: false
                  id: title
                  interface:
                    settings:
                      helpText: Post Title
                    widgetId: singleLine
                  localized: true
                  name: Title
                  omitted: false
                  required: true
                  type: Symbol
                  validations:
                  - unique: true
    '''

    expected_output = {
        'post': [
            {
                'fieldId': 'content',
                'settings': {
                    'helpText': 'Primary Post Content'
                },
                'widgetId': 'markdown'
            },
            {
                'fieldId': 'media',
                'widgetId': 'assetLinkEditor'
            },
            {
                'fieldId': 'title',
                'settings': {
                    'helpText': 'Post Title'
                },
                'widgetId': 'singleLine'
            }
        ]
    }

    schema = yaml.load(input_schema)
    result = tasks._extract_interface_controls_from_schema(schema)
    assert result == expected_output