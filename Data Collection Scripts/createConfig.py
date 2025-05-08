def createConfig(country, template, walk, mot):
    config_in = template
    config_out_mot = mot
    config_out_walk = walk

    replace_txt = 'country'
    walk = 'walking'
    mot = 'motorised'

    # Open the input file in read mode
    with open(config_in, 'r') as input_file:
        # Read the contents of the file
        file_contents = input_file.read()

    # Perform the replacement operation
    mot_contents = file_contents.replace(replace_txt, country)

    walk_contents = mot_contents.replace(mot, walk)

    # Open the output file in write mode
    with open(config_out_mot, 'w') as output_file:
        # Write the modified contents to the output file
        output_file.write(mot_contents)
        
    with open(config_out_walk, 'w') as output_file:
        # Write the modified contents to the output file
        output_file.write(walk_contents)


    print(f'Configs created. Mot config written to {config_out_mot}, Walk config written to {config_out_walk}')